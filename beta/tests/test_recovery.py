"""Recovery and verification use real token storage with a synthetic email transport."""

import time

import pytest
from sqlalchemy import select

from landwolf.db import AccountAction


class FixtureMailer:
    enabled = True

    def __init__(self):
        self.messages = []

    async def send(self, email, purpose, token):
        self.messages.append((email, purpose, token))


@pytest.fixture
def mailer(client):
    value = FixtureMailer()
    client.app.state.mailer = value
    return value


def request_reset(client, headers, email="investor@example.com"):
    return client.post("/api/auth/recovery", json={"email": email}, headers=headers)


def test_recovery_responses_do_not_reveal_account_existence(client, signed_in, mailer):
    known = request_reset(client, signed_in)
    unknown = request_reset(client, signed_in, "missing@example.com")
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(mailer.messages) == 1
    assert mailer.messages[0][2] not in known.text
    with client.app.state.factory() as session:
        stored = session.scalar(select(AccountAction))
        assert stored.token_hash != mailer.messages[0][2]


def test_reset_is_one_use_and_revokes_sessions(client, signed_in, mailer):
    request_reset(client, signed_in)
    token = mailer.messages[0][2]
    password = "New synthetic passphrase 941!"
    response = client.post(
        "/api/auth/reset-password", json={"token": token, "password": password}, headers=signed_in
    )
    assert response.status_code == 200
    assert client.get("/api/sources").status_code == 401
    assert (
        client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": password},
            headers=signed_in,
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "investor@example.com", "password": "Test-only passphrase 847!"},
            headers=signed_in,
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "investor@example.com", "password": password},
            headers=signed_in,
        ).status_code
        == 200
    )


def test_verification_requires_session_csrf_and_correct_token_purpose(client, signed_in, mailer):
    assert (
        client.post(
            "/api/auth/verification",
            json={},
            headers={"Origin": "http://testserver", "X-LandWolf-Client": "web"},
        ).status_code
        == 403
    )
    assert client.post("/api/auth/verification", json={}, headers=signed_in).status_code == 202
    token = mailer.messages[0][2]
    assert (
        client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": "New synthetic passphrase 941!"},
            headers=signed_in,
        ).status_code
        == 400
    )
    assert (
        client.post("/api/auth/verify-email", json={"token": token}, headers=signed_in).status_code
        == 200
    )
    assert client.get("/api/session").json()["email_verified"] is True
    assert (
        client.post("/api/auth/verify-email", json={"token": token}, headers=signed_in).status_code
        == 400
    )


def test_expired_and_malformed_tokens_fail_without_echo(client, signed_in, mailer):
    request_reset(client, signed_in)
    token = mailer.messages[0][2]
    with client.app.state.factory() as session, session.begin():
        session.scalar(select(AccountAction)).expires_at = int(time.time()) - 1
    response = client.post(
        "/api/auth/reset-password",
        json={"token": token, "password": "New synthetic passphrase 941!"},
        headers=signed_in,
    )
    assert response.status_code == 400 and token not in response.text
    response = client.post(
        "/api/auth/verify-email", json={"token": "bad-private-input"}, headers=signed_in
    )
    assert response.status_code == 422 and "bad-private-input" not in response.text


def test_recovery_disabled_is_explicit_and_does_not_issue_tokens(client, signed_in):
    assert request_reset(client, signed_in).status_code == 503
    with client.app.state.factory() as session:
        assert session.scalar(select(AccountAction)) is None


def test_cross_origin_recovery_and_rate_limits(client, signed_in, mailer):
    assert request_reset(client, {**signed_in, "Origin": "https://evil.example"}).status_code == 403
    for _ in range(3):
        assert request_reset(client, signed_in).status_code == 202
    assert request_reset(client, signed_in).status_code == 429


def test_delivery_failure_invalidates_issued_token(client, signed_in, mailer):
    async def fail(*args):
        raise RuntimeError("Synthetic email outage")

    mailer.send = fail
    assert request_reset(client, signed_in).status_code == 202
    with client.app.state.factory() as session:
        assert session.scalar(select(AccountAction)) is None
