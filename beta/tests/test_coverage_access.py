"""Coverage administration must not change customer inventory or Hunt access."""

import pytest
from sqlalchemy import select

from landwolf.db import Account, BillingExemption


@pytest.mark.parametrize("path", ["/api/sources", "/api/capabilities"])
def test_coverage_requires_owner_not_just_a_session(client, signed_in, path):
    assert client.get(path).status_code == 403
    with client.app.state.factory() as session:
        account = session.scalar(select(Account))
        client.app.state.settings.owner_account_id = account.id
    assert client.get(path).status_code == 200
    client.app.state.settings.owner_account_id = "another-owner"
    assert (
        client.get(path, headers={"X-Owner": "true"}, params={"is_owner": True}).status_code == 403
    )
    client.post("/api/auth/logout", headers=signed_in, json={})
    assert client.get(path).status_code == 401


def test_customer_search_and_hunt_results_survive_coverage_restriction(
    client, signed_in, inventory
):
    with client.app.state.factory() as session:
        account_id = session.scalar(select(Account.id))
    customer = client.post("/api/search", json={}, headers=signed_in).json()
    assert customer["total"] == 2
    assert customer["sources"] == []
    assert isinstance(customer["data_attention"], bool)
    saved = client.post(
        "/api/hunts",
        headers=signed_in,
        json={
            "name": "Customer Hunt",
            "criteria": {"mode": "fixed", "states": ["TX"], "min_acres": 1, "max_acres": 50},
        },
    )
    assert saved.status_code == 201
    hunt_id = saved.json()["id"]
    customer_matches = client.get(f"/api/hunts/{hunt_id}/matches")
    assert customer_matches.status_code == 200
    client.app.state.settings.owner_account_id = account_id
    owner = client.post("/api/search", json={}, headers=signed_in).json()
    assert owner["results"] == customer["results"]
    assert owner["total"] == customer["total"]
    assert owner["sources"]
    owner_matches = client.get(f"/api/hunts/{hunt_id}/matches").json()
    for group in ("matches", "needs_review"):
        assert owner_matches[group] == customer_matches.json()[group]
    assert len(owner_matches["matches"]) + len(owner_matches["needs_review"]) == 2


def test_complimentary_access_does_not_grant_coverage_admin(client, signed_in):
    with client.app.state.factory() as session, session.begin():
        account_id = session.scalar(select(Account.id))
        session.add(
            BillingExemption(
                id="fixture-grant",
                account_id=account_id,
                status="active",
                reason="Fixture",
                granted_by_account_id=account_id,
                granted_at=1,
                created_at=1,
                updated_at=1,
            )
        )
    assert client.get("/api/session").json()["access_override"] == "complimentary"
    assert client.get("/api/sources").status_code == 403
    assert client.get("/api/capabilities").status_code == 403
