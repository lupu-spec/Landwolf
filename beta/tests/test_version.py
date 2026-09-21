"""Release identity must be useful, consistent and safe to expose publicly."""

import json
import tomllib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from landwolf.version import VERSION


@pytest.mark.parametrize("commit", [None, "", "not-a-commit", "x" * 40, "a" * 41])
def test_missing_or_invalid_build_identity_is_unknown(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, commit: str | None
) -> None:
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    if commit is not None:
        monkeypatch.setenv("RENDER_GIT_COMMIT", commit)
    response = client.get("/api/version")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"version": VERSION, "environment": "test", "commit": None}


def test_release_identity_matches_health_and_session(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    commit = "0123456789abcdef" * 2 + "01234567"
    monkeypatch.setenv("RENDER_GIT_COMMIT", commit)
    assert client.get("/api/version").json()["commit"] == commit
    assert client.get("/api/health").json()["version"] == VERSION
    assert client.get("/api/session").json()["version"] == VERSION
    assert client.get("/api/session").json()["authenticated"] is False
    assert client.get("/api/sources").status_code == 401


def test_distribution_versions_match_runtime() -> None:
    root = Path(__file__).resolve().parents[1]
    assert tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"] == VERSION
    assert json.loads((root / "package.json").read_text())["version"] == VERSION
    npm_lock = json.loads((root / "package-lock.json").read_text())
    assert npm_lock["version"] == npm_lock["packages"][""]["version"] == VERSION
    lock = tomllib.loads((root / "uv.lock").read_text())
    app = next(package for package in lock["package"] if package["name"] == "landwolf-beta")
    assert app["version"] == VERSION
