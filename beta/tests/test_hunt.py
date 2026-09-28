"""Hunt contract, account isolation and deterministic ranking."""

import time
from datetime import UTC, datetime

import pytest
from conftest import register
from fastapi.testclient import TestClient
from sqlalchemy import select

from landwolf.db import (
    Account,
    HuntEvent,
    Listing,
    SchemaVersion,
    SourceState,
    database,
    initialize,
)
from landwolf.hunt import Criteria, distance_miles, evaluate
from landwolf.schemas import PropertyRecord


def criteria(**changes: object) -> dict[str, object]:
    return {
        "mode": "fixed",
        "states": ["TX"],
        "min_acres": 10,
        "max_acres": 50,
        "preferred_min": 15,
        "preferred_max": 25,
        "max_price": 300000,
        "max_price_per_acre": 12000,
        **changes,
    }


def record(**changes: object) -> PropertyRecord:
    return PropertyRecord.model_validate(
        {
            "id": "glo-test",
            "tract": "123",
            "title": "Synthetic test land",
            "source_url": "https://www.glo.texas.gov/example",
            "retrieved_at": datetime.now(UTC).isoformat(),
            "acres": 20,
            "asking_price": 120000,
            "latitude": 32.5,
            "longitude": -96.5,
            **changes,
        }
    )


def test_score_and_unknown_vs_failure() -> None:
    now = int(time.time())
    source = SourceState(id="tx_glo_public", last_success=now)
    result = evaluate(record(), Criteria(**criteria()), source, now=now)
    assert result["eligibility"] == "eligible"
    assert result["score"] == 84
    assert (
        evaluate(record(acres=51), Criteria(**criteria()), source, now=now)["eligibility"]
        == "excluded"
    )
    assert (
        evaluate(record(acres=None), Criteria(**criteria()), source, now=now)["eligibility"]
        == "needs_review"
    )
    assert (
        evaluate(record(), Criteria(**criteria()), None, now=now)["eligibility"] == "needs_review"
    )
    assert (
        evaluate(record(price_kind="Minimum bid"), Criteria(**criteria()), source, now=now)[
            "eligibility"
        ]
        == "needs_review"
    )


def test_radius_and_invalid_contract() -> None:
    assert distance_miles(0, 0, 0, 1) == pytest.approx(69.09, rel=0.01)
    for invalid in [
        criteria(min_acres=30, max_acres=10),
        criteria(states=["TX", "TX"]),
        criteria(mode="auction", max_price_per_acre=100),
        criteria(center_lat=32, radius_miles=50),
    ]:
        with pytest.raises(ValueError):
            Criteria(**invalid)


def test_api_lifecycle_and_isolation(client: TestClient, signed_in: dict[str, str]) -> None:
    with client.app.state.factory() as session, session.begin():
        session.add(SourceState(id="tx_glo_public", last_success=int(time.time())))
        item = record()
        session.add(
            Listing(
                id=item.id, source=item.source, active=True, payload=item.model_dump(mode="json")
            )
        )
    created = client.post(
        "/api/hunts", json={"name": "Texas land", "criteria": criteria()}, headers=signed_in
    )
    assert created.status_code == 201, created.text
    assert len(created.json()["matches"]) == 1
    hunt_id = created.json()["id"]
    assert client.get(f"/api/hunts/{hunt_id}/events").json()["events"] == []
    assert len(client.get(f"/api/hunts/{hunt_id}/matches").json()["matches"]) == 1
    other = register(client, "second@example.com")
    assert client.get(f"/api/hunts/{hunt_id}/matches").status_code == 404
    assert (
        client.patch(f"/api/hunts/{hunt_id}", json={"active": False}, headers=other).status_code
        == 404
    )
    # Log back into the first account to exercise revision and deletion.
    login = client.post(
        "/api/auth/login",
        json={"email": "investor@example.com", "password": "Test-only passphrase 847!"},
        headers=other,
    )
    auth = {**signed_in, "X-CSRF-Token": login.json()["csrf"]}
    edited = client.patch(
        f"/api/hunts/{hunt_id}",
        json={"criteria": criteria(min_acres=25, preferred_min=25)},
        headers=auth,
    )
    assert edited.status_code == 200
    assert edited.json()["revision"] == 2
    assert client.get(f"/api/hunts/{hunt_id}/matches").json()["matches"] == []
    assert client.request("DELETE", f"/api/hunts/{hunt_id}", headers=auth, json={}).json() == {
        "deleted": True
    }
    assert client.get(f"/api/hunts/{hunt_id}/matches").status_code == 404


def test_hunts_require_authentication(client: TestClient) -> None:
    assert client.get("/api/hunts").status_code == 401
    assert client.get("/api/hunts/unknown/matches").status_code == 401


def test_schema_v4_upgrade_preserves_accounts(tmp_path) -> None:
    engine, factory = database(f"sqlite:///{tmp_path / 'upgrade.db'}")
    initialize(engine)
    with factory() as session, session.begin():
        session.add(Account(id="fixture", email="fixture@example.com", password_hash="fixture"))
        session.get(SchemaVersion, 5).version = 4
    initialize(engine)
    with factory() as session:
        assert session.get(Account, "fixture") is not None
        assert session.get(SchemaVersion, 5) is not None
    engine.dispose()


def test_new_match_event_is_idempotent(client: TestClient, signed_in: dict[str, str]) -> None:
    with client.app.state.factory() as session, session.begin():
        session.add(SourceState(id="tx_glo_public", last_success=int(time.time())))
    created = client.post(
        "/api/hunts", json={"name": "Search", "criteria": criteria()}, headers=signed_in
    )
    hunt_id = created.json()["id"]
    with client.app.state.factory() as session, session.begin():
        item = record()
        session.add(
            Listing(
                id=item.id, source=item.source, active=True, payload=item.model_dump(mode="json")
            )
        )
    client.get(f"/api/hunts/{hunt_id}/matches")
    client.get(f"/api/hunts/{hunt_id}/matches")
    with client.app.state.factory() as session:
        assert len(session.scalars(select(HuntEvent)).all()) <= 1
