"""Account persistence, location handoff, validation, and safe migration regressions."""

from pathlib import Path
from uuid import uuid4

import pytest
from conftest import register
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from landwolf.db import (
    Account,
    Base,
    Listing,
    SavedProperty,
    SavedRecord,
    SchemaVersion,
    database,
    initialize,
)
from landwolf.main import create_app
from landwolf.saved import source_location
from landwolf.schemas import PropertyRecord


def manual(**changes: object) -> dict:
    return {
        "manual_id": str(uuid4()),
        "title": "Synthetic saved property",
        "location": {"address": "123 Fixture St, Test City, TX 75000"},
        **changes,
    }


def test_manual_save_retry_reload_account_isolation_and_delete(
    client: TestClient,
    signed_in: dict[str, str],
) -> None:
    payload = manual()
    first = client.post("/api/saved", json=payload, headers=signed_in)
    assert first.status_code == 200
    entry = first.json()
    assert entry["property"] is None and entry["location_origin"] == "user"
    assert client.post("/api/saved", json=payload, headers=signed_in).json()["id"] == entry["id"]
    assert client.get("/api/saved").json()["total"] == 1
    assert client.post("/api/search", json={}, headers=signed_in).json()["total"] == 0
    client.post("/api/auth/logout", json={}, headers=signed_in)
    second = register(client, "second@example.com")
    assert client.get("/api/saved").json()["total"] == 0
    path = "/api/saved/" + entry["id"]
    assert client.get(path).status_code == 404
    assert (
        client.patch(
            path,
            json={
                "title": "Attempted overwrite",
                "location": {"latitude": 1, "longitude": 2},
                "revision": 1,
            },
            headers=second,
        ).status_code
        == 404
    )
    client.request("DELETE", path, json={}, headers=second)
    client.post("/api/auth/logout", json={}, headers=second)
    login = client.post(
        "/api/auth/login",
        json={
            "email": "investor@example.com",
            "password": "Test-only passphrase 847!",
        },
        headers=signed_in,
    )
    headers = {**signed_in, "X-CSRF-Token": login.json()["csrf"]}
    assert client.get(path).json()["location"]["address"] == payload["location"]["address"]
    assert client.request("DELETE", path, json={}, headers=headers).status_code == 200
    assert client.get("/api/saved").json()["total"] == 0


def test_bookmark_location_override_survives_restart_without_changing_source(
    client: TestClient,
    signed_in: dict[str, str],
    inventory: None,
) -> None:
    path = "/api/saved/glo-99001"
    assert client.put(path, json={}, headers=signed_in).status_code == 200
    source = client.get(path).json()
    assert source["location"] == {"address": None, "latitude": 32.48455, "longitude": -98.5175}
    assert source["location_origin"] == "source"
    edited = {
        "title": "My research location",
        "location": {"latitude": 35.7804, "longitude": -78.6391},
        "revision": source["revision"],
    }
    response = client.patch(path, json=edited, headers=signed_in)
    assert response.status_code == 200
    assert response.json()["revision"] == 2
    assert client.patch(path, json=edited, headers=signed_in).status_code == 409
    assert client.put(path, json={}, headers=signed_in).status_code == 200
    record = client.get("/api/properties/glo-99001").json()
    assert record["latitude"] == 32.48455 and record["longitude"] == -98.5175
    assert record["research_location"]["latitude"] == 35.7804
    assert record["location_origin"] == "user"
    assert client.get(path).json()["revision"] == 2
    with TestClient(create_app(client.app.state.settings)) as restarted:
        restarted.cookies.update(client.cookies)
        assert restarted.get(path).json()["location"] == response.json()["location"]
    # An inactive property remains in Saved with its research location.
    with client.app.state.factory() as session, session.begin():
        session.get(Listing, "glo-99001").active = False
    assert client.get("/api/saved").json()["results"][0]["property"]["active"] is False


def test_manual_coordinates_zero_and_pagination(
    client: TestClient, signed_in: dict[str, str]
) -> None:
    for index in range(3):
        assert (
            client.post(
                "/api/saved",
                json=manual(
                    title=f"Synthetic {index}",
                    location={"latitude": 0, "longitude": 0},
                ),
                headers=signed_in,
            ).status_code
            == 200
        )
    first = client.get("/api/saved?page_size=2").json()
    second = client.get("/api/saved?page_size=2&page=2").json()
    assert first["total"] == second["total"] == 3
    assert len(first["results"]) == 2 and len(second["results"]) == 1
    assert not {x["id"] for x in first["results"]} & {x["id"] for x in second["results"]}
    assert first["results"][0]["location"]["latitude"] == 0
    assert client.get("/api/saved?page_size=101").status_code == 422


@pytest.mark.parametrize(
    "location",
    [
        {},
        {"latitude": 1},
        {"longitude": 2},
        {"latitude": 91, "longitude": 2},
        {"latitude": 1, "longitude": -181},
        {"latitude": "NaN", "longitude": 2},
        {"latitude": True, "longitude": 2},
        {"address": " " * 12},
        {"address": "x" * 241},
        {"address": "123 Test\nSt, City, TX 75000"},
        {"address": "123 Test St, City, TX 75000", "latitude": 1, "longitude": 2},
        {"address": "123 Test St, City, TX 75000", "basis": "Source-published coordinate"},
    ],
)
def test_invalid_locations_do_not_create_saved_records(
    client: TestClient,
    signed_in: dict[str, str],
    location: dict,
) -> None:
    assert (
        client.post("/api/saved", json=manual(location=location), headers=signed_in).status_code
        == 422
    )
    assert client.get("/api/saved").json()["total"] == 0


def test_saved_security_guards(client: TestClient, signed_in: dict[str, str]) -> None:
    payload = manual()
    entry = client.post("/api/saved", json=payload, headers=signed_in).json()
    update = {"title": "Edited", "location": payload["location"], "revision": 1}
    for headers in [
        {**signed_in, "X-CSRF-Token": "bad"},
        {**signed_in, "Origin": "https://evil.example.com"},
    ]:
        assert client.post("/api/saved", json=manual(), headers=headers).status_code == 403
        assert (
            client.patch("/api/saved/" + entry["id"], json=update, headers=headers).status_code
            == 403
        )
    client.post("/api/auth/logout", json={}, headers=signed_in)
    assert client.get("/api/saved").status_code == 401
    assert client.get("/api/saved/" + entry["id"]).status_code == 401
    assert client.post("/api/saved", json=manual(), headers=signed_in).status_code == 401
    assert (
        client.patch("/api/saved/" + entry["id"], json=update, headers=signed_in).status_code == 401
    )


@pytest.mark.parametrize(
    "source", ["usda_resales", "irs_auctions", "us_treasury", "tx_glo_public", "ak_dnr"]
)
def test_full_source_address_handoff_is_not_limited_to_two_feeds(source: str) -> None:
    record = PropertyRecord(
        id="fixture",
        tract="fixture",
        title="Fixture",
        source=source,
        source_url="https://www.glo.texas.gov",
        retrieved_at="2099-01-01",
        location_description="123 Fixture St, Test City, TX 75000",
    )
    point = source_location(record)
    assert point and point.address == record.location_description and point.latitude is None
    for value in [None, "tract 123", "123 county parcel", "123 Test St, City, CA 75000", "x" * 301]:
        record.location_description = value
        assert source_location(record) is None


def test_migration_copies_bookmarks_and_preserves_existing_records(tmp_path: Path) -> None:
    engine, _ = database(f"sqlite:///{tmp_path / 'v1.db'}")
    Base.metadata.create_all(
        engine,
        tables=[
            table
            for table in Base.metadata.sorted_tables
            if table.name != SavedRecord.__tablename__
        ],
    )
    with Session(engine) as session, session.begin():
        session.add(SchemaVersion(version=1))
        session.add(
            Account(
                id="fixture-account",
                email="migration@example.com",
                password_hash="synthetic-hash",
                created_at=123,
            )
        )
        session.add(
            Listing(
                id="fixture-listing",
                source="tx_glo_public",
                active=False,
                payload={"title": "Original fixture"},
            )
        )
        session.flush()
        session.add(
            SavedProperty(
                account_id="fixture-account", listing_id="fixture-listing", created_at=456
            )
        )
    initialize(engine)
    initialize(engine)
    with Session(engine) as session:
        assert session.scalars(select(SchemaVersion.version)).all() == [2]
        row = session.get(SavedRecord, ("fixture-account", "fixture-listing"))
        assert row.title == "Original fixture" and row.created_at == 456 and row.revision == 1
        assert row.research_location is None
        assert session.get(SavedProperty, ("fixture-account", "fixture-listing")).created_at == 456
        assert session.get(Account, "fixture-account").password_hash == "synthetic-hash"
        assert session.get(Listing, "fixture-listing").active is False
    engine.dispose()


def test_unknown_schema_fails_before_creating_new_tables(tmp_path: Path) -> None:
    engine, _ = database(f"sqlite:///{tmp_path / 'unknown.db'}")
    SchemaVersion.__table__.create(engine)
    with Session(engine) as session, session.begin():
        session.add(SchemaVersion(version=999))
    with pytest.raises(RuntimeError, match="Unsupported"):
        initialize(engine)
    assert not inspect(engine).has_table(SavedRecord.__tablename__)
    engine.dispose()
