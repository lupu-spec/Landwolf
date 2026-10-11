import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from landwolf.db import Listing


def test_filters_sorting_pagination_and_uncovered_sources(
    client: TestClient, signed_in: dict[str, str], inventory: None
) -> None:
    def search(**query: object) -> dict:
        response = client.post("/api/search", json=query, headers=signed_in)
        assert response.status_code == 200
        return response.json()

    result = search(page_size=1)
    assert result["total"] == 2
    assert result["results"][0]["id"] == "glo-99001"
    assert search(page=2, page_size=1)["results"][0]["id"] == "glo-99002"
    assert search(location="  eastland  ")["total"] == 1
    assert search(min_acres=11)["total"] == 1
    assert search(max_price=100000)["total"] == 1
    assert search(sort="price_desc")["results"][0]["id"] == "glo-99002"
    assert search(sort="acres_desc")["results"][0]["acres"] == 20
    assert search(location="' OR 1=1 --")["total"] == 0
    assert search(page=999)["results"] == []
    assert search(state="CA")["coverage_supported"] is True
    assert search(category="tax_sale")["coverage_supported"] is True
    assert search(category="pre_foreclosure")["coverage_supported"] is False
    assert search(location="missing")["coverage_supported"] is True


@pytest.mark.parametrize(
    "query",
    [
        {"page": 0},
        {"min_acres": -1},
        {"page_size": 101},
        {"category": "injected"},
        {"location": "x" * 101},
    ],
)
def test_search_rejects_bad_contracts(
    client: TestClient, signed_in: dict[str, str], query: dict
) -> None:
    assert client.post("/api/search", json=query, headers=signed_in).status_code == 422


def test_missing_detail_is_404(client: TestClient, signed_in: dict[str, str]) -> None:
    assert client.get("/api/properties/missing").status_code == 404


def test_map_uses_filtered_inventory_not_list_page(
    client: TestClient, signed_in: dict[str, str], inventory: None
) -> None:
    with client.app.state.factory() as session, session.begin():
        template = session.get(Listing, "glo-99001")
        session.add(
            Listing(
                id="no-point",
                source=template.source,
                active=True,
                payload={
                    **template.payload,
                    "id": "no-point",
                    "asking_price": 1,
                    "latitude": None,
                    "longitude": None,
                },
            )
        )

    def search(**query: object) -> dict:
        response = client.post("/api/search", json=query, headers=signed_in)
        assert response.status_code == 200
        return response.json()

    first = search(page_size=1)
    assert first["results"][0]["latitude"] is None
    assert first["map_total"] == 2
    assert {r["id"] for r in first["map_results"]} == {"glo-99001", "glo-99002"}
    assert first["map_results"] == search(page=2, page_size=1)["map_results"]
    assert first["map_results"] == search(page=999)["map_results"]
    assert search(location="eastland")["map_total"] == 1
    assert search(min_acres=11)["map_total"] == 1
    assert search(max_price=1)["map_results"] == []
    assert search(state="CA")["map_results"] == []
    assert search(category="tax_sale")["map_results"] == []
    assert search(source="mi_dnr")["map_results"] == []
    assert search(location="missing")["map_total"] == 0
    assert set(first["map_results"][0]) == {"id", "tract", "asking_price", "latitude", "longitude"}
    assert client.post("/api/auth/logout", headers=signed_in, json={}).status_code == 200
    assert client.post("/api/search", json={}, headers=signed_in).status_code == 401


def test_map_response_is_bounded_and_does_not_include_inactive_or_expired(
    client: TestClient, signed_in: dict[str, str], inventory: None
) -> None:
    with client.app.state.factory() as session, session.begin():
        template = session.get(Listing, "glo-99001")
        for i in range(1001):
            session.add(
                Listing(
                    id=f"bounded-{i:04}",
                    source=template.source,
                    active=True,
                    payload={**template.payload, "id": f"bounded-{i:04}"},
                )
            )
        session.add(
            Listing(
                id="expired",
                source=template.source,
                active=True,
                payload={**template.payload, "id": "expired", "auction_date": "2000-01-01"},
            )
        )
    result = client.post("/api/search", json={}, headers=signed_in).json()
    assert result["map_total"] == 1003
    assert len(result["map_results"]) == result["map_limit"] == 1000
    assert len(result["results"]) == 12
    assert not {"expired", "glo-99003"} & {r["id"] for r in result["map_results"]}
    with client.app.state.factory() as session:
        assert len(list(session.scalars(select(Listing)))) == 1005
