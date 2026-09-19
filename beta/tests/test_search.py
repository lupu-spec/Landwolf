import pytest
from fastapi.testclient import TestClient


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
