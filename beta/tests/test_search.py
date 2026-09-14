import pytest
from conftest import register
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
    assert search(state="CA")["coverage_supported"] is False
    assert search(category="tax_sale")["coverage_supported"] is False
    assert search(location="missing")["coverage_supported"] is True


def test_saved_properties_belong_to_each_account_and_survive_logout(
    client: TestClient, signed_in: dict[str, str], inventory: None
) -> None:
    for _ in range(2):
        assert client.put("/api/saved/glo-99001", json={}, headers=signed_in).status_code == 200
    assert (
        client.post("/api/search", json={"saved_only": True}, headers=signed_in).json()["total"]
        == 1
    )
    client.post("/api/auth/logout", json={}, headers=signed_in)
    second = register(client, "second@example.com")
    assert not client.get("/api/properties/glo-99001").json()["saved"]
    assert (
        client.post("/api/search", json={"saved_only": True}, headers=second).json()["total"] == 0
    )
    client.request("DELETE", "/api/saved/glo-99001", json={}, headers=second)
    client.post("/api/auth/logout", json={}, headers=second)
    response = client.post(
        "/api/auth/login",
        json={
            "email": "investor@example.com",
            "password": "Test-only passphrase 847!",
        },
        headers=signed_in,
    )
    first = {**signed_in, "X-CSRF-Token": response.json()["csrf"]}
    assert client.get("/api/properties/glo-99001").json()["saved"]
    assert (
        client.request("DELETE", "/api/saved/glo-99001", json={}, headers=first).status_code == 200
    )
    assert not client.get("/api/properties/glo-99001").json()["saved"]


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


def test_missing_detail_and_save_are_404(client: TestClient, signed_in: dict[str, str]) -> None:
    assert client.get("/api/properties/missing").status_code == 404
    assert client.put("/api/saved/missing", json={}, headers=signed_in).status_code == 404
