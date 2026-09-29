"""Explicit staging-only save probe; never run automatically against production.

Creates one disposable account, verifies saved IDs through authenticated API reads,
and removes only Hunts created by that account. No credentials are logged or saved.
"""

import http.cookiejar
import json
import secrets
import sys
import urllib.error
import urllib.request
import uuid

ORIGIN = "https://landwolf-premium-staging.onrender.com"


def main() -> int:
    email = f"hunt-save-qa-{uuid.uuid4().hex}@example.com"
    password = secrets.token_urlsafe(32)
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
    csrf = ""
    report: dict[str, object] = {"environment": "staging", "checks": []}
    checks: list[dict[str, object]] = []
    created_ids: set[str] = set()

    def request(path: str, method: str = "GET", payload=None):
        headers = {
            "Origin": ORIGIN,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-LandWolf-Client": "web",
        }
        if csrf:
            headers["X-CSRF-Token"] = csrf
        body = None
        if payload is not None:
            body = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(ORIGIN + path, body, headers, method=method)
        try:
            with opener.open(req, timeout=90) as response:  # noqa: S310
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                detail = json.loads(exc.read())
            except (ValueError, UnicodeError):
                detail = {"detail": "Non-JSON error response"}
            return exc.code, detail

    try:
        status, version = request("/api/version")
        report["version_status"], report["version"] = status, version
        if status != 200 or version.get("environment") != "staging":
            raise RuntimeError("Refusing to test a non-staging service")
        status, health = request("/api/health")
        report["health_status"], report["health"] = status, health
        status, login = request(
            "/api/auth/register", "POST", {"email": email, "password": password}
        )
        if status != 201 or not login.get("csrf"):
            raise RuntimeError(f"Disposable registration failed: HTTP {status}")
        csrf = login["csrf"]
        for label, lower, upper in [
            ("default", 5, 50),
            ("small", 0.01, 5),
            ("large", 50, 500),
            ("500-plus", 500, 10000000),
            ("all-acreages", 0.01, 10000000),
        ]:
            status, saved = request(
                "/api/hunts",
                "POST",
                {
                    "name": f"QA {label}",
                    "criteria": {
                        "mode": "fixed",
                        "states": [],
                        "min_acres": lower,
                        "max_acres": upper,
                    },
                },
            )
            check: dict[str, object] = {"case": label, "post_status": status}
            checks.append(check)
            if status != 201 or not saved.get("id"):
                check["error"] = saved.get("detail", "Save did not return an ID")
                continue
            hunt_id = saved["id"]
            created_ids.add(hunt_id)
            check["saved_id"] = hunt_id
            status, listed = request("/api/hunts")
            check["get_status"] = status
            check["persisted"] = status == 200 and any(
                row["id"] == hunt_id for row in listed.get("hunts", [])
            )
            if label == "default":
                status, updated = request(
                    f"/api/hunts/{hunt_id}", "PATCH", {"name": "QA renamed Hunt"}
                )
                check["patch_status"] = status
                check["rename_returned"] = updated.get("name") == "QA renamed Hunt"
                # Fresh login, not the in-memory response from the create request.
                opener = urllib.request.build_opener(
                    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
                )
                csrf = ""
                status, login = request(
                    "/api/auth/login", "POST", {"email": email, "password": password}
                )
                if status != 200 or not login.get("csrf"):
                    raise RuntimeError(f"Fresh login failed: HTTP {status}")
                csrf = login["csrf"]
                status, listed = request("/api/hunts")
                check["persisted_after_login"] = status == 200 and any(
                    row["id"] == hunt_id and row["name"] == "QA renamed Hunt"
                    for row in listed.get("hunts", [])
                )
            status, matches = request(f"/api/hunts/{hunt_id}/matches")
            check["matches_status"] = status
            if status == 200:
                check["match_count"] = len(matches.get("matches", []))
            else:
                check["matches_error"] = matches.get("detail", "Matching failed")
            status, _ = request(f"/api/hunts/{hunt_id}", "DELETE")
            check["delete_status"] = status
            if status == 200:
                created_ids.remove(hunt_id)
    except Exception as exc:
        # Never print exception reprs that might include request bodies or credentials.
        report["error_type"] = type(exc).__name__
    finally:
        for hunt_id in tuple(created_ids):
            try:
                status, _ = request(f"/api/hunts/{hunt_id}", "DELETE")
                if status == 200:
                    created_ids.remove(hunt_id)
            except Exception:
                pass
        report["checks"] = checks
        report["remaining_test_hunts"] = len(created_ids)
        print(json.dumps(report, indent=2))
    return int(
        bool(report.get("error_type"))
        or len(checks) != 5
        or bool(created_ids)
        or any(
            check.get("post_status") != 201
            or not check.get("persisted")
            or check.get("matches_status") != 200
            or check.get("delete_status") != 200
            for check in checks
        )
        or not checks[0].get("persisted_after_login")
    )


if __name__ == "__main__":
    sys.exit(main())
