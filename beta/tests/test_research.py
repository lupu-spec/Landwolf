"""Authentication, source contracts, bounded egress and honest missing-data behavior."""

import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from research_fixture import public_response
from sqlalchemy import select

from landwolf import research
from landwolf.db import Listing
from landwolf.research import (
    CENSUS,
    FEMA,
    NC,
    SOIL,
    SOIL_COLUMNS,
    USGS,
    JsonReader,
    ResearchBusy,
    ResearchPoint,
    ResearchQuery,
    ResearchService,
    ResearchUnavailable,
)

POINT = {"latitude": 35.7804, "longitude": -78.6391}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"latitude": 35},
        {"longitude": -78},
        {**POINT, "address": "1 Synthetic Way"},
        {**POINT, "listing_id": "fixture"},
        {"latitude": True, "longitude": 0},
        {"latitude": float("nan"), "longitude": 0},
        {"latitude": 91, "longitude": 0},
        {"latitude": 0, "longitude": -181},
        {"address": "        "},
        {"address": "1 Synthetic\nWay"},
        {"address": "x" * 241},
        {"listing_id": "../../secret"},
        {**POINT, "url": "http://localhost"},
        {"latitude": "0); DROP TABLE mapunit;--", "longitude": 0},
    ],
)
def test_rejects_invalid_or_ambiguous_query(payload: dict) -> None:
    with pytest.raises(ValidationError):
        ResearchQuery.model_validate(payload)


def lookup(handler=public_response, query=None, point=None):
    return asyncio.run(
        ResearchService(httpx.MockTransport(handler)).lookup(query or ResearchQuery(**POINT), point)
    )


def test_complete_reference_report_preserves_unknowns_and_excludes_owner_data() -> None:
    requests = []

    def handler(request):
        requests.append(request)
        return public_response(request)

    report = lookup(handler)
    assert report.status == "ready" and len(report.sources) == 5
    assert report.location.basis == "User-supplied coordinate"
    assert len(requests) == 6
    sources = {s.id: s for s in report.sources}
    terrain = {f.label: f.value for f in sources["usgs"].sections[0].facts}
    assert terrain["Elevation (meters)"] == "0.00"
    assert terrain["Acquisition date"] == "1/1/2020"
    parcel = {f.label: f.value for f in sources["nc_parcels"].sections[0].facts}
    assert parcel["Reported parcel value (USD)"] == "Not published"
    assert parcel["Reported improvement value (USD)"] == "0"
    assert parcel["Dataset transform date (UTC)"] == "2026-01-01"
    assert parcel["Record revised date (source text)"] == "2025-12-01"
    assert "OWNER FIELD" not in report.model_dump_json()
    parcel_request = next(r for r in requests if str(r.url).startswith(NC))
    assert "ownname" not in parcel_request.url.params["outFields"]
    soil_request = next(r for r in requests if str(r.url) == SOIL)
    assert soil_request.method == "POST"
    sql = json.loads(soil_request.content)["query"]
    assert "point (-78.6391000 35.7804000)" in sql
    assert "SELECT TOP 21" in sql and "Synthetic" not in sql


def test_address_is_approximate_and_no_parcel_claim_is_made() -> None:
    report = lookup(query=ResearchQuery(address="1 Synthetic Way, Fixture, NC 27000"))
    assert report.location.basis == "Census address approximation"
    assert "candidate parcels" in report.sources[-1].summary
    assert "tax values are not market values" in report.sources[-1].summary


@pytest.mark.parametrize("matches,status", [([], "no_match"), ([{}, {}], "ambiguous")])
def test_no_unique_address_match_stops_downstream_requests(matches, status) -> None:
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"result": {"addressMatches": matches}})

    report = lookup(handler, ResearchQuery(address="1 Synthetic Way, Fixture NC"))
    assert report.status == status and report.location is None
    assert len(calls) == 1


@pytest.mark.parametrize(
    "state,status,source_count", [("TX", "ready", 5), ("DC", "outside_coverage", 1)]
)
def test_state_scope_and_nc_parcel_coverage_are_explicit(state, status, source_count) -> None:
    calls = []

    def handler(request):
        calls.append(str(request.url))
        response = public_response(request)
        if str(request.url).startswith(CENSUS):
            data = response.json()
            data["result"]["geographies"]["States"] = [{"STUSAB": state}]
            return httpx.Response(200, json=data)
        return response

    report = lookup(handler)
    assert report.status == status and len(report.sources) == source_count
    assert not any(url.startswith(NC) for url in calls)
    if state == "TX":
        assert report.sources[-1].status == "not_applicable"


@pytest.mark.parametrize(
    "bad",
    [
        None,
        [],
        {"geographies": []},
        {"geographies": {"States": [None]}},
        {"geographies": {"States": [{"STUSAB": []}]}},
    ],
)
def test_malformed_census_fails_closed(bad) -> None:
    report = lookup(lambda request: httpx.Response(200, json={"result": bad}))
    assert report.status == "unavailable" and report.location is None


def test_published_coordinate_state_conflict_is_rejected() -> None:
    report = lookup(
        query=ResearchQuery(listing_id="glo-fixture"),
        point=ResearchPoint(
            **POINT, label="Synthetic listing", basis="Source-published coordinate", state="TX"
        ),
    )
    assert report.status == "unavailable" and report.location is None


@pytest.mark.parametrize(
    "endpoint,data,source,status",
    [
        (FEMA + "0/query", {"features": []}, "fema", "no_data"),
        (FEMA + "28/query", {"features": []}, "fema", "no_data"),
        (FEMA + "28/query", {"features": [], "exceededTransferLimit": True}, "fema", "unavailable"),
        (
            FEMA + "28/query",
            {"features": [{"attributes": {"FLD_ZONE": "X", "SFHA_TF": "?"}}]},
            "fema",
            "unavailable",
        ),
        (USGS, {"value": -999999}, "usgs", "no_data"),
        (USGS, {"value": "NaN"}, "usgs", "unavailable"),
        (USGS, {"value": 20, "attributes": None}, "usgs", "unavailable"),
        (SOIL, {"Table": []}, "soil", "no_data"),
        (SOIL, {"Table": [["Unexpected"]]}, "soil", "unavailable"),
        (SOIL, {"Table": [SOIL_COLUMNS] + [[None] * 9] * 21}, "soil", "unavailable"),
        (NC, {"features": []}, "nc_parcels", "no_data"),
        (
            NC,
            {
                "features": [
                    {"attributes": {"parno": "999", "stcntyfips": "37", "transfdate": 1e300}}
                ]
            },
            "nc_parcels",
            "unavailable",
        ),
    ],
)
def test_partial_source_failure_never_becomes_zero_risk(endpoint, data, source, status) -> None:
    def handler(request):
        if str(request.url).split("?")[0] == endpoint:
            return httpx.Response(200, json=data)
        return public_response(request)

    report = lookup(handler)
    assert report.status == "partial"
    changed = next(s for s in report.sources if s.id == source)
    assert changed.status == status and changed.sections == []
    assert len([s for s in report.sources if s.status == "ready"]) == 4
    if source == "fema" and status == "no_data":
        assert "risk is unknown" in changed.summary.lower()


def test_below_sea_elevation_and_multiple_candidates_are_preserved() -> None:
    def handler(request):
        response = public_response(request)
        if str(request.url).startswith(USGS):
            return httpx.Response(200, json={"value": -50, "attributes": {}})
        if str(request.url).startswith(NC):
            data = response.json()
            second = dict(data["features"][0]["attributes"], parno="FIXTURE-OTHER")
            data["features"].append({"attributes": second})
            return httpx.Response(200, json=data)
        return response

    report = lookup(handler)
    assert report.sources[2].sections[0].facts[0].value == "-50.00"
    assert len(report.sources[-1].sections) == 2


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(302, headers={"Location": "http://127.0.0.1/private"}),
        httpx.Response(200, text="html"),
        httpx.Response(200, json={"error": "SECRET UPSTREAM BODY"}),
        httpx.Response(200, json=[]),
        httpx.Response(
            200,
            content=b"x" * (research.MAX_BYTES + 1),
            headers={"Content-Type": "application/json"},
        ),
    ],
)
def test_reader_rejects_redirects_invalid_types_errors_and_oversized_responses(response) -> None:
    calls = []

    def handler(request):
        calls.append(request)
        return response

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises((ResearchUnavailable, httpx.HTTPStatusError)):
                await JsonReader(client).read(USGS)

    asyncio.run(run())
    assert len(calls) == 1


def test_reader_host_allowlist_retry_and_total_request_budget() -> None:
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503 if len(calls) == 1 else 200, json={})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            reader = JsonReader(client)
            with pytest.raises(ResearchUnavailable):
                await reader.read("http://169.254.169.254/latest/meta-data")
            assert not calls
            await reader.read(USGS)
            assert len(calls) == 2
            for _ in range(12):
                await reader.read(USGS)
            with pytest.raises(ResearchUnavailable):
                await reader.read(USGS)
            assert len(calls) == 14

    asyncio.run(run())


def test_cache_is_bounded_expires_and_does_not_share_mutable_reports(monkeypatch) -> None:
    clock = [1000.0]
    monkeypatch.setattr(research.time, "monotonic", lambda: clock[0])
    calls = []

    def handler(request):
        calls.append(request)
        return public_response(request)

    async def run():
        service = ResearchService(httpx.MockTransport(handler))
        query = ResearchQuery(**POINT)
        first = await service.lookup(query)
        first.sources.clear()
        second = await service.lookup(query)
        assert second.cached and len(second.sources) == 5 and len(calls) == 6
        clock[0] += 21601
        third = await service.lookup(query)
        assert not third.cached and len(calls) == 12
        for i in range(129):
            await service.lookup(ResearchQuery(latitude=30 + i / 1000, longitude=-78))
        assert len(service.cache) == 128
        service.active = 4
        with pytest.raises(ResearchBusy):
            await service.lookup(ResearchQuery(latitude=40, longitude=-78))
        assert service.active == 4

    asyncio.run(run())


def test_api_requires_auth_csrf_and_retains_existing_data(
    client: TestClient, inventory: None, signed_in: dict[str, str]
) -> None:
    client.app.state.research.transport = httpx.MockTransport(public_response)
    assert client.post("/api/research", json=POINT).status_code == 403
    with client.app.state.factory() as db:
        before = [r.payload for r in db.scalars(select(Listing).order_by(Listing.id))]
    response = client.post("/api/research", json=POINT, headers=signed_in)
    assert response.status_code == 200 and response.json()["status"] == "ready"
    with client.app.state.factory() as db:
        assert [r.payload for r in db.scalars(select(Listing).order_by(Listing.id))] == before
    assert (
        client.post("/api/research", json={"listing_id": "missing"}, headers=signed_in).status_code
        == 404
    )
    client.app.state.research.active = 4
    busy = client.post("/api/research", json={"latitude": 1, "longitude": 1}, headers=signed_in)
    assert busy.status_code == 503 and busy.headers["retry-after"] == "5"
    client.post("/api/auth/logout", json={}, headers=signed_in)
    assert client.post("/api/research", json=POINT).status_code == 401


def test_api_uses_published_coordinates_and_rate_limits(client, signed_in, inventory) -> None:
    def handler(request):
        response = public_response(request)
        if str(request.url).startswith(CENSUS):
            assert request.url.params["x"] == "-98.5175"
            data = response.json()
            data["result"]["geographies"]["States"] = [{"STUSAB": "TX"}]
            return httpx.Response(200, json=data)
        return response

    client.app.state.research.transport = httpx.MockTransport(handler)
    response = client.post("/api/research", json={"listing_id": "glo-99001"}, headers=signed_in)
    assert response.status_code == 200
    assert response.json()["location"]["basis"] == "Source-published coordinate"
    for _ in range(11):
        assert (
            client.post(
                "/api/research", json={"listing_id": "glo-99001"}, headers=signed_in
            ).status_code
            == 200
        )
    assert client.post("/api/research", json=POINT, headers=signed_in).status_code == 429


def test_listing_without_coordinates_requires_user_location(client, signed_in) -> None:
    from conftest import seed_national

    seed_national(client.app.state.factory)
    response = client.post("/api/research", json={"listing_id": "fixture-ar"}, headers=signed_in)
    assert response.status_code == 422 and "No published point" in response.json()["detail"]
