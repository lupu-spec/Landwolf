import time
from pathlib import Path

import pytest
from conftest import register
from fastapi import HTTPException, Request, Response
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from landwolf import auth
from landwolf.config import Settings
from landwolf.db import Account, LoginSession, RateBucket
from landwolf.main import create_app
from landwolf.schemas import AnalysisInput


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("POST", "/api/search", {}),
        ("GET", "/api/sources", None),
        ("GET", "/api/properties/glo-99001", None),
    ],
)
def test_property_access_requires_server_session(
    client: TestClient, method: str, path: str, payload: object
) -> None:
    assert client.request(method, path, json=payload).status_code == 401


def test_analysis_requires_session(client: TestClient, scenario: AnalysisInput) -> None:
    assert client.post("/api/analysis", json=scenario.model_dump()).status_code == 401


def test_password_hash_cookie_storage_and_logout(
    client: TestClient, signed_in: dict[str, str]
) -> None:
    token = client.cookies.get(auth.COOKIE)
    assert token is not None
    with client.app.state.factory() as session:
        account = session.scalar(select(Account))
        login = session.scalar(select(LoginSession))
        assert account.password_hash.startswith("$argon2id$")
        assert auth.PASSWORDS.verify(account.password_hash, "Test-only passphrase 847!")
        assert login.token_hash != token
        assert login.token_hash == auth.digest(token)
    assert client.get("/api/session").json()["authenticated"]
    response = client.post("/api/auth/logout", json={}, headers=signed_in)
    assert response.status_code == 200
    client.cookies.set(auth.COOKIE, token)
    assert client.get("/api/sources").status_code == 401


def test_cookie_is_http_only_same_site_and_secure_on_https(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "cookie@example.com",
            "password": "Test-only passphrase 847!",
        },
        headers={"Origin": "http://testserver", "X-LandWolf-Client": "web"},
    )
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert Settings(public_origin="https://beta.example.com").secure_cookies


@pytest.mark.parametrize(
    "change",
    [
        {"Origin": "https://evil.example.com"},
        {"X-CSRF-Token": "incorrect"},
        {"X-CSRF-Token": b"\xe9" * 43},
        {"X-LandWolf-Client": ""},
        {"Sec-Fetch-Site": "cross-site"},
    ],
)
def test_csrf_and_origin_are_enforced(
    client: TestClient, signed_in: dict[str, str], change: dict[str, str | bytes]
) -> None:
    response = client.post("/api/search", json={}, headers={**signed_in, **change})
    assert response.status_code == 403


def test_expired_sessions_cannot_be_renewed(client: TestClient, signed_in: dict[str, str]) -> None:
    with client.app.state.factory() as session, session.begin():
        login = session.scalar(select(LoginSession))
        login.expires_at = int(time.time()) - 1
    assert client.post("/api/search", json={}, headers=signed_in).status_code == 401
    response = client.get("/api/session")
    assert response.json()["authenticated"] is False
    assert "set-cookie" not in response.headers


def test_persistent_session_survives_inactivity_and_renews_legacy_cookie(
    client: TestClient, signed_in: dict[str, str]
) -> None:
    now = int(time.time())
    token = client.cookies.get(auth.COOKIE)
    with client.app.state.factory() as session, session.begin():
        login = session.scalar(select(LoginSession))
        login.last_seen = now - 180 * 86400
        login.expires_at = now + 60
    response = client.get("/api/session")
    assert response.json()["authenticated"] is True
    assert response.json()["csrf"] == signed_in["X-CSRF-Token"]
    assert client.cookies.get(auth.COOKIE) == token
    cookie = response.headers["set-cookie"].lower()
    assert "max-age=31536000" in cookie and "expires=" in cookie
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/" in cookie
    assert response.headers["cache-control"] == "no-store"
    with client.app.state.factory() as session:
        login = session.scalar(select(LoginSession))
        assert now + 365 * 86400 <= login.expires_at <= int(time.time()) + 365 * 86400
        assert login.last_seen >= now
    assert client.post("/api/search", json={}, headers=signed_in).status_code == 200


def test_cookie_deletion_cannot_restore_authentication(
    client: TestClient, signed_in: dict[str, str]
) -> None:
    client.cookies.clear()
    response = client.get("/api/session")
    assert response.json()["authenticated"] is False
    assert "set-cookie" not in response.headers
    assert client.post("/api/search", json={}, headers=signed_in).status_code == 401


def test_revocation_during_renewal_does_not_recreate_session(
    client: TestClient, signed_in: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    token = client.cookies.get(auth.COOKIE)
    request = Request({"type": "http", "headers": [(b"cookie", f"{auth.COOKIE}={token}".encode())]})
    response = Response()
    with client.app.state.factory() as session:
        original_scalar = session.scalar

        def revoke_before_update(statement):
            session.execute(
                delete(LoginSession).where(LoginSession.token_hash == auth.digest(token))
            )
            session.commit()
            return original_scalar(statement)

        monkeypatch.setattr(session, "scalar", revoke_before_update)
        with pytest.raises(HTTPException) as exc:
            auth.authenticate(request, session, client.app.state.settings, response=response)
        assert exc.value.status_code == 401
        assert "set-cookie" not in response.headers
    with client.app.state.factory() as session:
        assert session.get(LoginSession, auth.digest(token)) is None


def test_logout_revokes_renewed_session(client: TestClient, signed_in: dict[str, str]) -> None:
    token = client.cookies.get(auth.COOKIE)
    assert client.get("/api/session").json()["authenticated"]
    response = client.post("/api/auth/logout", json={}, headers=signed_in)
    assert response.status_code == 200
    assert "max-age=0" in response.headers["set-cookie"].lower()
    client.cookies.set(auth.COOKIE, token)
    assert client.get("/api/session").json()["authenticated"] is False
    with client.app.state.factory() as session:
        assert session.get(LoginSession, auth.digest(token)) is None


@pytest.mark.parametrize("days", [0, 401])
def test_persistent_cookie_lifetime_is_bounded(days: int) -> None:
    with pytest.raises(ValueError):
        Settings(session_days=days)


def test_login_rotates_session_and_wrong_password_fails(client: TestClient) -> None:
    headers = register(client)
    original = client.cookies.get(auth.COOKIE)
    response = client.post(
        "/api/auth/login",
        json={
            "email": "INVESTOR@example.com",
            "password": "Test-only passphrase 847!",
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert client.cookies.get(auth.COOKIE) != original
    with client.app.state.factory() as session:
        assert session.get(LoginSession, auth.digest(original)) is None
    response = client.post(
        "/api/auth/login",
        json={
            "email": "investor@example.com",
            "password": "Incorrect test password",
        },
        headers=headers,
    )
    assert response.status_code == 401
    assert "password" not in response.json().get("input", {})


def test_rate_limit_is_shared_and_contains_no_raw_identity(client: TestClient) -> None:
    with client.app.state.factory() as session:
        auth.limit(session, "private@example.com", 1, seconds=3600)
    with client.app.state.factory() as session:
        with pytest.raises(HTTPException) as exc:
            auth.limit(session, "private@example.com", 1, seconds=3600)
        assert exc.value.status_code == 429
        assert all(len(bucket.key) == 64 for bucket in session.scalars(select(RateBucket)))


def test_validation_does_not_echo_password_and_body_is_bounded(client: TestClient) -> None:
    response = client.post("/api/auth/register", json={"email": "invalid", "password": "short"})
    assert response.status_code == 422
    assert "short" not in response.text
    assert "invalid" not in response.text
    assert client.post("/api/auth/register", content=b"x" * 16385).status_code == 413


def test_host_security_headers_and_no_paywall(client: TestClient) -> None:
    assert client.get("/api/health", headers={"Host": "attacker.example.com"}).status_code == 400
    response = client.get("/api/session")
    assert response.headers["cache-control"] == "no-store"
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-frame-options"] == "DENY"
    assert client.get("/api/health").json()["payments_enabled"] is False
    assert client.post("/api/checkout", json={}).status_code == 404
    assert not any("stripe" in route.path.lower() for route in client.app.routes)


def test_production_rejects_unsafe_settings() -> None:
    with pytest.raises(ValueError):
        Settings(environment="production")
    with pytest.raises(ValueError):
        Settings(payments_enabled=True)
    with pytest.raises(ValueError):
        Settings(public_origin="https://name:password@example.com")


def test_https_response_sets_secure_cookie_and_hsts(tmp_path: Path) -> None:
    settings = Settings(
        environment="test",
        public_origin="https://testserver",
        database_url=f"sqlite:///{tmp_path / 'secure.db'}",
        auto_sync=False,
    )
    with TestClient(create_app(settings), base_url="https://testserver") as client:
        response = client.post(
            "/api/auth/register",
            json={
                "email": "secure@example.com",
                "password": "Test-only passphrase 847!",
            },
            headers={"Origin": "https://testserver", "X-LandWolf-Client": "web"},
        )
        assert response.status_code == 201
        cookie = response.headers["set-cookie"].lower()
        assert "; secure" in cookie and "; httponly" in cookie
        assert response.headers["strict-transport-security"] == "max-age=31536000"


def test_password_work_is_bounded_and_recovers(client: TestClient) -> None:
    with auth.password_work(), auth.password_work():
        response = client.post(
            "/api/auth/register",
            json={
                "email": "bounded@example.com",
                "password": "Test-only passphrase 847!",
            },
            headers={"Origin": "http://testserver", "X-LandWolf-Client": "web"},
        )
        assert response.status_code == 503
        assert response.headers["retry-after"] == "2"
    assert register(client, "bounded@example.com")


def test_configuration_errors_hide_connection_inputs() -> None:
    sensitive = "test-only-connection-value"
    with pytest.raises(ValueError) as exc:
        Settings(environment="production", database_url=sensitive)
    assert sensitive not in str(exc.value)
