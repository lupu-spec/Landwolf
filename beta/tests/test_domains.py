"""Production cutover preserves account data without widening same-origin writes."""

from pathlib import Path
from urllib.parse import urlsplit

import pytest
from conftest import seed
from fastapi.testclient import TestClient

from landwolf.config import Settings
from landwolf.main import create_app

ORIGINS = (
    "https://landwolf.ai",
    "https://www.landwolf.ai",
    "https://landwolf-free-beta.onrender.com",
)
CREDENTIALS = {
    "email": "cutover-fixture@example.com",
    "password": "Synthetic cutover passphrase 847!",
}


def domain_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'domains.db'}",
        public_origin=ORIGINS[0],
        additional_origins=ORIGINS[1:],
        auto_sync=False,
    )


def test_production_environment_has_explicit_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANDWOLF_PUBLIC_ORIGIN", "https://LandWolf.ai/")
    monkeypatch.setenv(
        "LANDWOLF_ADDITIONAL_ORIGINS",
        '["https://www.landwolf.ai","https://landwolf-free-beta.onrender.com"]',
    )
    settings = Settings(
        _env_file=None,
        environment="production",
        database_url="postgresql://fixture@localhost/landwolf_ci",
    )
    assert settings.trusted_origins == ORIGINS
    assert settings.payments_enabled is False
    assert settings.secure_cookies


@pytest.mark.parametrize(
    "origin",
    [
        "http://www.landwolf.ai",
        "https://localhost",
        "https://testserver",
        "https://127.0.0.1",
        "https://[::1]",
        "https://www.landwolf.ai:443",
        "https://www.landwolf.ai:invalid",
        "https://*.landwolf.ai",
        "https://www.landwolf.ai/path",
        "https://www.landwolf.ai?query=1",
        "https://www.landwolf.ai#fragment",
        "https://user@www.landwolf.ai",
        "https://@www.landwolf.ai",
        "https://www.landwolf.ai\\attacker.example",
        "https://www.landwolf.ai\n",
        "https://www.landwolf.ai\t",
        "https://www.landwolf.ai ",
        "https://www.landwolf.ai\x7f",
        "https://LandWolf.ai/",
        "",
    ],
)
def test_invalid_or_duplicate_alias_stops_production(origin: str) -> None:
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            environment="production",
            database_url="postgresql://fixture@localhost/landwolf_ci",
            public_origin=ORIGINS[0],
            additional_origins=(origin,),
        )


def test_alias_count_is_bounded() -> None:
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            public_origin=ORIGINS[0],
            additional_origins=tuple(f"https://host{i}.example.com" for i in range(5)),
        )


def test_cookie_scheme_cannot_be_ambiguous() -> None:
    with pytest.raises(ValueError, match="same scheme"):
        Settings(
            _env_file=None,
            public_origin=ORIGINS[0],
            additional_origins=("http://localhost:8000",),
        )


@pytest.mark.parametrize("host_origin", ORIGINS)
@pytest.mark.parametrize("request_origin", ORIGINS)
def test_only_same_origin_can_register(
    tmp_path: Path, host_origin: str, request_origin: str
) -> None:
    with TestClient(create_app(domain_settings(tmp_path)), base_url=host_origin) as client:
        assert client.get("/api/health").json()["payments_enabled"] is False
        assert client.get("/api/sources").status_code == 401
        response = client.post(
            "/api/auth/register",
            json=CREDENTIALS,
            headers={"Origin": request_origin, "X-LandWolf-Client": "web"},
        )
        assert response.status_code == (201 if host_origin == request_origin else 403)
        if response.status_code == 201:
            cookie = response.headers["set-cookie"].lower()
            assert "; secure" in cookie and "; httponly" in cookie
            assert "samesite=strict" in cookie and "domain=" not in cookie


@pytest.mark.parametrize(
    "headers,expected",
    [
        ({"Origin": "https://attacker.example"}, 403),
        ({"Origin": "null"}, 403),
        ({"Origin": ""}, 403),
        ({"Origin": "https://landwolf.ai.attacker.example"}, 403),
        ({"Host": "attacker.example", "X-Forwarded-Host": "landwolf.ai"}, 400),
        ({"Host": "landwolf.ai:8443"}, 403),
        ({"Host": "www.landwolf.ai", "X-Forwarded-Host": "landwolf.ai"}, 403),
        ({"Origin": "https://attacker.example", "X-Forwarded-Host": "attacker.example"}, 403),
        ({"Sec-Fetch-Site": "cross-site"}, 403),
        ({"X-LandWolf-Client": ""}, 403),
        ({"X-Forwarded-Host": "attacker.example", "X-Forwarded-Proto": "http"}, 201),
    ],
)
def test_untrusted_headers_cannot_widen_access(
    tmp_path: Path, headers: dict[str, str], expected: int
) -> None:
    with TestClient(create_app(domain_settings(tmp_path)), base_url=ORIGINS[0]) as client:
        response = client.post(
            "/api/auth/register",
            json=CREDENTIALS,
            headers={"Origin": ORIGINS[0], "X-LandWolf-Client": "web", **headers},
        )
        assert response.status_code == expected


def test_accounts_survive_signing_in_on_new_domain(tmp_path: Path) -> None:
    app = create_app(domain_settings(tmp_path))
    with TestClient(app, base_url=ORIGINS[2]) as client:
        seed(app.state.factory)
        old_headers = {"Origin": ORIGINS[2], "X-LandWolf-Client": "web"}
        registration = client.post("/api/auth/register", json=CREDENTIALS, headers=old_headers)
        assert registration.status_code == 201
        old_headers["X-CSRF-Token"] = registration.json()["csrf"]

        # Browser cookies do not cross hosts. The same account can sign in again.
        assert client.get(f"{ORIGINS[0]}/api/sources").status_code == 401
        new_headers = {"Origin": ORIGINS[0], "X-LandWolf-Client": "web"}
        login = client.post(f"{ORIGINS[0]}/api/auth/login", json=CREDENTIALS, headers=new_headers)
        assert login.status_code == 200
        new_headers["X-CSRF-Token"] = login.json()["csrf"]
        search = client.post(f"{ORIGINS[0]}/api/search", json={}, headers=new_headers)
        assert search.status_code == 200
        assert [item["id"] for item in search.json()["results"]] == ["glo-99001", "glo-99002"]
        assert (
            client.post(
                f"{ORIGINS[0]}/api/search",
                json={},
                headers={**new_headers, "X-CSRF-Token": old_headers["X-CSRF-Token"]},
            ).status_code
            == 403
        )
        for origin in ORIGINS[1:]:
            assert (
                client.post(
                    f"{ORIGINS[0]}/api/search", json={}, headers={**new_headers, "Origin": origin}
                ).status_code
                == 403
            )
        assert client.post(f"{ORIGINS[0]}/api/checkout", json={}).status_code == 404


def test_local_origin_ports_remain_supported(tmp_path: Path) -> None:
    settings = domain_settings(tmp_path).model_copy(
        update={"public_origin": "http://localhost:8000", "additional_origins": ()}
    )
    with TestClient(create_app(settings), base_url=settings.public_origin) as client:
        response = client.post(
            "/api/auth/register",
            json=CREDENTIALS,
            headers={
                "Origin": settings.public_origin,
                "Host": urlsplit(settings.public_origin).netloc,
                "X-LandWolf-Client": "web",
            },
        )
        assert response.status_code == 201
        assert "; secure" not in response.headers["set-cookie"].lower()
