"""Cohort consent, time boundaries, isolation, and server-side access contracts."""

from datetime import UTC, datetime

import pytest
from conftest import register
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_admin_billing import owner_and_user

from landwolf import feedback
from landwolf.db import Account, FeedbackAudit, FeedbackEnrollment, FeedbackResponse

ANSWERS = {
    "usage": "not_used",
    "last_attempted_task": "I have not used the product yet.",
    "blocker": "I need to test it on my next property search.",
    "feature_request": "No changes yet.",
    "feature_reason": "I need experience before recommending a change.",
    "priority": "low",
    "value_rating": None,
    "no_changes": True,
}
ACCEPT = {"terms_version": "investor-pilot-v1", "accepted_terms": True, "baseline": ANSWERS}


def enroll(client):
    _, user, owner_headers = owner_and_user(client)
    response = client.post(
        f"/api/admin/accounts/{user.id}/feedback-pilot", headers=owner_headers, json={}
    )
    assert response.status_code == 201, response.text
    client.post("/api/auth/logout", headers=owner_headers, json={})
    response = client.post(
        "/api/auth/login",
        headers={"Origin": "http://testserver", "X-LandWolf-Client": "web"},
        json={"email": "customer@example.com", "password": "Test-only passphrase 847!"},
    )
    headers = {
        "Origin": "http://testserver",
        "X-LandWolf-Client": "web",
        "X-CSRF-Token": response.json()["csrf"],
    }
    return user, headers


def test_no_public_enrollment_or_admin_access(client: TestClient):
    headers = register(client)
    assert client.get("/api/feedback").json()["state"] == "none"
    assert client.post("/api/feedback/accept", headers=headers, json=ACCEPT).status_code == 403
    for path in ["/api/admin/feedback", "/api/admin/feedback/responses"]:
        assert client.get(path).status_code == 403
    assert (
        client.post(
            "/api/admin/accounts/other/feedback-pilot", headers=headers, json={}
        ).status_code
        == 403
    )
    assert client.post("/api/search", headers=headers, json={}).status_code == 200


def test_consent_atomic_and_duplicate_accept_preserves_dates(client: TestClient):
    user, headers = enroll(client)
    assert client.get("/api/feedback").json()["state"] == "invited"
    assert (
        client.post(
            "/api/feedback/accept", headers=headers, json={**ACCEPT, "accepted_terms": False}
        ).status_code
        == 422
    )
    assert client.post("/api/feedback/accept", json=ACCEPT).status_code == 403
    accepted = client.post("/api/feedback/accept", headers=headers, json=ACCEPT)
    assert accepted.status_code == 200, accepted.text
    state = accepted.json()
    assert state["state"] == "active"
    assert state["completed_surveys"] == ["baseline"]
    again = client.post("/api/feedback/accept", headers=headers, json=ACCEPT)
    assert again.status_code == 200, again.text
    assert again.json()["expires_at"] == state["expires_at"]
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(FeedbackResponse)) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(FeedbackAudit)
                .where(FeedbackAudit.action == "accept")
            )
            == 1
        )
        row = session.get(FeedbackEnrollment, user.id)
        assert row is not None and row.accepted_at is not None
        start = datetime.fromtimestamp(row.accepted_at, UTC)
        end = datetime.fromtimestamp(row.expires_at, UTC)
        assert (end.year * 12 + end.month) - (start.year * 12 + start.month) == 3


def test_due_grace_gate_completion_and_fixed_expiry(client: TestClient, monkeypatch):
    user, headers = enroll(client)
    state = client.post("/api/feedback/accept", headers=headers, json=ACCEPT).json()
    start, expiry = state["accepted_at"], state["expires_at"]
    with client.app.state.factory() as session:
        account = session.get(Account, user.id)
        before = feedback.status(session, account, now=start + 14 * 86400 - 1)
        assert before["due_survey"] is None
        due = feedback.status(session, account, now=start + 14 * 86400)
        assert due["due_survey"]["key"] == "day14" and due["access_allowed"]
        grace = feedback.status(session, account, now=start + 21 * 86400 - 1)
        assert grace["access_allowed"]
    monkeypatch.setattr(feedback, "_now", lambda: start + 21 * 86400)
    blocked = client.post("/api/search", headers=headers, json={})
    assert blocked.status_code == 403, blocked.text
    assert client.get("/api/hunts").status_code == 200
    assert client.get("/api/session").status_code == 200
    assert client.get("/api/feedback").json()["state"] == "feedback_required"
    body = {"survey_key": "day14", "survey_version": 1, "answers": ANSWERS}
    result = client.post("/api/feedback/responses", headers=headers, json=body)
    assert result.status_code == 200, result.text
    assert result.json()["access_allowed"]
    assert client.post("/api/search", headers=headers, json={}).status_code == 200
    assert client.post("/api/feedback/responses", headers=headers, json=body).status_code == 200
    assert result.json()["expires_at"] == expiry
    monkeypatch.setattr(feedback, "_now", lambda: expiry)
    assert client.get("/api/feedback").json()["state"] == "expired"
    assert client.post("/api/search", headers=headers, json={}).status_code == 403
    assert client.post("/api/auth/logout", headers=headers, json={}).status_code == 200


def test_reject_future_version_blank_and_cross_account(client: TestClient):
    user, headers = enroll(client)
    client.post("/api/feedback/accept", headers=headers, json=ACCEPT)
    for changes in [
        {"survey_version": 2},
        {"answers": {**ANSWERS, "blocker": "   "}},
        {"account_id": user.id},
        {"answers": {**ANSWERS, "value_rating": 6}},
        {"answers": {**ANSWERS, "feature_request": "x" * 10000}},
    ]:
        body = {"survey_key": "day14", "survey_version": 1, "answers": ANSWERS, **changes}
        assert client.post("/api/feedback/responses", headers=headers, json=body).status_code == 422
    assert (
        client.post(
            "/api/feedback/responses",
            headers=headers,
            json={"survey_key": "day85", "survey_version": 1, "answers": ANSWERS},
        ).status_code
        == 409
    )
    client.post("/api/auth/logout", headers=headers, json={})
    other = register(client, "separate@example.com")
    assert client.get("/api/feedback").json()["state"] == "none"
    assert client.post("/api/feedback/accept", headers=other, json=ACCEPT).status_code == 403


@pytest.mark.parametrize("day", [0, 13, 14, 20, 21, 30, 60, 85, 100])
def test_never_extend_expiry_from_status_reads(client: TestClient, day: int):
    user, headers = enroll(client)
    state = client.post("/api/feedback/accept", headers=headers, json=ACCEPT).json()
    with client.app.state.factory() as session:
        account = session.get(Account, user.id)
        observed = feedback.status(session, account, now=state["accepted_at"] + day * 86400)
        assert observed["expires_at"] == state["expires_at"]


def test_schema_six_upgrade_preserves_accounts_and_is_idempotent(tmp_path):
    from landwolf.db import SCHEMA_VERSION, Base, SchemaVersion, database, initialize

    engine, factory = database(f"sqlite:///{tmp_path / 'old.db'}")
    Base.metadata.create_all(
        engine,
        tables=[
            table
            for table in Base.metadata.sorted_tables
            if not table.name.startswith("lw2_feedback_")
        ],
    )
    with factory() as session, session.begin():
        session.add(SchemaVersion(version=6))
        session.add(
            Account(id="fixture-account", email="migration@example.com", password_hash="fixture")
        )
    initialize(engine)
    initialize(engine)
    with factory() as session:
        assert session.get(Account, "fixture-account") is not None
        assert session.scalars(select(SchemaVersion.version)).all() == [SCHEMA_VERSION]
        assert session.scalar(select(func.count()).select_from(FeedbackResponse)) == 0
    engine.dispose()


@pytest.mark.parametrize(
    "start,end",
    [
        ("2026-11-30T15:25:03+00:00", "2027-02-28T15:25:03+00:00"),
        ("2027-11-30T15:25:03+00:00", "2028-02-29T15:25:03+00:00"),
        ("2026-01-31T15:25:03+00:00", "2026-04-30T15:25:03+00:00"),
    ],
)
def test_calendar_months_not_ninety_days(start, end):
    assert feedback.three_months_after(int(datetime.fromisoformat(start).timestamp())) == int(
        datetime.fromisoformat(end).timestamp()
    )


def test_all_protected_read_routes_deny_expired_pilot(client: TestClient, monkeypatch):
    _, headers = enroll(client)
    accepted = client.post("/api/feedback/accept", headers=headers, json=ACCEPT).json()
    monkeypatch.setattr(feedback, "_now", lambda: accepted["expires_at"])
    for path in [
        "/api/sources",
        "/api/properties/unknown",
        "/api/hunts/unknown/matches",
        "/api/hunts/unknown/events",
    ]:
        response = client.get(path)
        assert response.status_code == 403, (path, response.text)
        assert response.json()["detail"]["code"] == "PILOT_EXPIRED"
    assert client.get("/api/hunts").status_code == 200
    assert client.get("/api/feedback").status_code == 200


def test_acceptance_failure_rolls_back_baseline_and_clock(client: TestClient, monkeypatch):
    user, headers = enroll(client)

    def fail(*args, **kwargs):
        raise RuntimeError("Synthetic audit failure")

    monkeypatch.setattr(feedback, "_audit", fail)
    with pytest.raises(RuntimeError, match="Synthetic audit failure"):
        client.post("/api/feedback/accept", headers=headers, json=ACCEPT)
    with client.app.state.factory() as session:
        row = session.get(FeedbackEnrollment, user.id)
        assert row.state == "invited" and row.accepted_at is None and row.expires_at is None
        assert session.scalar(select(func.count()).select_from(FeedbackResponse)) == 0


def test_reminder_poll_does_not_extend_idle_session(client: TestClient):
    import time

    from landwolf.db import LoginSession

    register(client)
    observed = int(time.time()) - 120
    with client.app.state.factory() as session, session.begin():
        login = session.scalar(select(LoginSession))
        login.last_seen = observed
    assert client.get("/api/feedback").status_code == 200
    with client.app.state.factory() as session:
        assert session.scalar(select(LoginSession)).last_seen == observed
