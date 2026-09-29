"""Hunt persistence must not depend on the listing-matching transaction."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, event, select
from sqlalchemy.exc import SQLAlchemyError

from landwolf import hunt
from landwolf.db import Hunt, HuntMatch, Listing


def test_bad_catalog_record_cannot_discard_hunt(client: TestClient, signed_in: dict[str, str]):
    with client.app.state.factory() as session, session.begin():
        session.add(
            Listing(
                id="invalid-fixture",
                source="tx_glo_public",
                active=True,
                payload={"id": "invalid-fixture"},
            )
        )
    response = client.post(
        "/api/hunts",
        headers=signed_in,
        json={
            "name": "Keep my preferences",
            "criteria": {
                "mode": "fixed",
                "states": [],
                "min_acres": 5,
                "max_acres": 50,
            },
        },
    )
    assert response.status_code == 201, response.text
    saved = response.json()
    assert saved["matching_status"] == "unavailable"
    assert "saved" in saved["matching_message"].lower()
    with client.app.state.factory() as session:
        stored = session.get(Hunt, saved["id"])
        assert stored is not None
        assert stored.name == "Keep my preferences"
    assert client.get("/api/hunts").json()["hunts"][0]["id"] == saved["id"]
    failed = client.get(f"/api/hunts/{saved['id']}/matches")
    assert failed.status_code == 503
    assert "Your Hunt is saved" in failed.json()["detail"]
    assert "validation errors" not in failed.text
    with client.app.state.factory() as session, session.begin():
        session.execute(delete(Listing).where(Listing.id == "invalid-fixture"))
    assert client.get(f"/api/hunts/{saved['id']}/matches").status_code == 200


@pytest.mark.parametrize(
    "failure", [ValueError("Private source detail"), SQLAlchemyError("Private SQL")]
)
def test_matching_failure_preserves_save_and_redacts_error(
    client: TestClient,
    signed_in: dict[str, str],
    monkeypatch,
    failure,
):
    def unavailable(session, row, **kwargs):
        session.add(
            HuntMatch(
                hunt_id=row.id,
                listing_id="rollback-fixture",
                revision=1,
                score=80,
                fingerprint="fixture",
                updated_at=1,
            )
        )
        session.flush()
        raise failure

    monkeypatch.setattr(hunt, "refresh", unavailable)
    response = client.post(
        "/api/hunts",
        headers=signed_in,
        json={
            "name": "Keep this Hunt",
            "criteria": {
                "mode": "fixed",
                "states": [],
                "min_acres": 5,
                "max_acres": 50,
            },
        },
    )
    assert response.status_code == 201, response.text
    assert "Private" not in response.text
    with client.app.state.factory() as session:
        assert session.scalar(select(Hunt).where(Hunt.id == response.json()["id"])) is not None
        assert session.scalars(select(HuntMatch)).all() == []


def test_failed_database_insert_is_not_reported_as_saved(
    client: TestClient,
    signed_in: dict[str, str],
):
    engine = client.app.state.factory.kw["bind"]

    def reject_insert(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO lw2_hunts"):
            raise SQLAlchemyError("Synthetic insert failure")

    event.listen(engine, "before_cursor_execute", reject_insert)
    try:
        response = client.post(
            "/api/hunts",
            headers=signed_in,
            json={
                "name": "Do not claim saved",
                "criteria": {
                    "mode": "fixed",
                    "states": [],
                    "min_acres": 5,
                    "max_acres": 50,
                },
            },
        )
    finally:
        event.remove(engine, "before_cursor_execute", reject_insert)
    assert response.status_code == 503
    assert "could not be saved" in response.json()["detail"]
    assert client.get("/api/hunts").json()["hunts"] == []


def test_save_limit_and_pause_remain_enforced(client: TestClient, signed_in: dict[str, str]):
    payload = {
        "name": "Limit fixture",
        "criteria": {
            "mode": "fixed",
            "states": [],
            "min_acres": 5,
            "max_acres": 50,
        },
    }
    ids = []
    for _ in range(3):
        response = client.post("/api/hunts", headers=signed_in, json=payload)
        assert response.status_code == 201
        assert response.json()["matching_status"] == "ready"
        ids.append(response.json()["id"])
    rejected = client.post("/api/hunts", headers=signed_in, json=payload)
    assert rejected.status_code == 409
    assert len(client.get("/api/hunts").json()["hunts"]) == 3
    assert (
        client.patch(f"/api/hunts/{ids[0]}", headers=signed_in, json={"active": False}).status_code
        == 200
    )
    assert client.post("/api/hunts", headers=signed_in, json=payload).status_code == 201
