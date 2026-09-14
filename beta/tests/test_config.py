"""Deployment origin and HTTP security boundaries with synthetic platform settings."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from landwolf.config import Settings
from landwolf.main import create_app


@pytest.fixture
def render_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://landwolf-config-test.onrender.com")
    monkeypatch.delenv("LANDWOLF_PUBLIC_ORIGIN", raising=False)


def test_production_uses_assigned_render_origin(render_environment: None) -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        database_url="postgresql://user@localhost/landwolf_beta",
    )
    assert settings.public_origin == "https://landwolf-config-test.onrender.com"
    assert settings.secure_cookies
    assert settings.database_url.startswith("postgresql+psycopg://")


@pytest.mark.parametrize(
    "origin",
    [
        "",
        "http://landwolf-config-test.onrender.com",
        "https://pending.invalid",
        "https://onrender.com",
        "https://.onrender.com",
        "https://landwolf-config-test.onrender.com.attacker.example",
        "https://landwolf-config-test.onrender.com:8443",
        "https://user@landwolf-config-test.onrender.com",
        "https://landwolf-config-test.onrender.com/path",
        "https://landwolf-config-test.onrender.com?query=1",
        "https://landwolf-config-test.onrender.com#fragment",
    ],
)
def test_invalid_render_origin_stops_production(
    render_environment: None, monkeypatch: pytest.MonkeyPatch, origin: str
) -> None:
    monkeypatch.setenv("RENDER_EXTERNAL_URL", origin)
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            environment="production",
            database_url="postgresql://user@localhost/landwolf_beta",
        )


def test_missing_render_origin_stops_production(
    render_environment: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("RENDER_EXTERNAL_URL")
    with pytest.raises(ValueError):
        Settings(_env_file=None, environment="production")


def test_explicit_custom_domain_takes_precedence(
    render_environment: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LANDWOLF_PUBLIC_ORIGIN", "https://beta.example.com/")
    settings = Settings(
        _env_file=None,
        environment="production",
        database_url="postgresql://user@localhost/landwolf_beta",
    )
    assert settings.public_origin == "https://beta.example.com"
    assert Settings(_env_file=None, public_origin="https://override.example.com").public_origin == (
        "https://override.example.com"
    )
    monkeypatch.setenv("LANDWOLF_PUBLIC_ORIGIN", "")
    with pytest.raises(ValueError):
        Settings(_env_file=None, environment="production")


def test_non_render_development_keeps_local_origin(
    render_environment: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("RENDER")
    assert Settings(_env_file=None).public_origin == "http://127.0.0.1:8000"


@pytest.mark.parametrize("value", ["false", "False", "FALSE"])
def test_render_environment_accepts_disabled_payments(
    render_environment: None, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("LANDWOLF_ENVIRONMENT", "production")
    monkeypatch.setenv("LANDWOLF_DATABASE_URL", "postgresql://user@localhost/landwolf_beta")
    monkeypatch.setenv("LANDWOLF_PAYMENTS_ENABLED", value)
    settings = Settings(_env_file=None)
    assert settings.payments_enabled is False
    assert settings.public_origin == "https://landwolf-config-test.onrender.com"


@pytest.mark.parametrize("value", ["true", "True", "1", "0", "off", ""])
def test_environment_cannot_enable_or_ambiguously_configure_payments(
    render_environment: None, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("LANDWOLF_PAYMENTS_ENABLED", value)
    with pytest.raises(ValueError, match="Payments must remain disabled"):
        Settings(_env_file=None)


def test_assigned_origin_enforces_host_csrf_and_secure_cookie(
    render_environment: None, tmp_path: Path
) -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'render.db'}",
        auto_sync=False,
    )
    with TestClient(create_app(settings), base_url=settings.public_origin) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/health", headers={"Host": "attacker.example"}).status_code == 400
        credentials = {
            "email": "render-config@example.com",
            "password": "Synthetic test passphrase 857!",
        }
        headers = {"Origin": settings.public_origin, "X-LandWolf-Client": "web"}
        rejected = client.post(
            "/api/auth/register",
            json=credentials,
            headers={**headers, "Origin": "https://attacker.example"},
        )
        assert rejected.status_code == 403
        response = client.post("/api/auth/register", json=credentials, headers=headers)
        assert response.status_code == 201
        cookie = response.headers["set-cookie"].lower()
        assert "; secure" in cookie and "; httponly" in cookie and "samesite=strict" in cookie
        assert response.headers["strict-transport-security"] == "max-age=31536000"
