#!/usr/bin/env python3
from __future__ import annotations

import os
import secrets
import sys
import uuid
import httpx

def die(message: str) -> int:
    print(f"SMOKE TEST FAILED: {message}", file=sys.stderr)
    return 1

def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable {name}")
    return value

def main() -> int:
    try:
        base_url = require_env("SMOKE_BASE_URL").rstrip("/") + "/"
        allowed_origin = require_env("SMOKE_ALLOWED_ORIGIN")
        blocked_origin = require_env("SMOKE_BLOCKED_ORIGIN")
        timeout = float(os.getenv("SMOKE_TIMEOUT_SECONDS", "15"))
    except Exception as exc:
        return die(str(exc))

    if not base_url.startswith("https://"):
        return die("SMOKE_BASE_URL must use HTTPS.")
    if not allowed_origin.startswith("https://"):
        return die("SMOKE_ALLOWED_ORIGIN must use HTTPS.")
    if allowed_origin == blocked_origin:
        return die("Allowed and blocked CORS origins must differ.")

    password = os.getenv("SMOKE_TEST_PASSWORD") or secrets.token_urlsafe(24) + "Aa1!"
    domain = os.getenv("SMOKE_TEST_EMAIL_DOMAIN", "example.invalid").strip()
    email = f"smoke-{uuid.uuid4().hex}@{domain}"

    with httpx.Client(
        base_url=base_url,
        timeout=timeout,
        follow_redirects=False,
        headers={"User-Agent": "property-intelligence-release-smoke/1.0"},
    ) as client:
        # Startup/readiness validation
        r = client.get("api/health")
        if r.status_code != 200:
            return die(f"/api/health returned HTTP {r.status_code}, expected 200.")
        try:
            health = r.json()
        except Exception:
            return die("/api/health did not return JSON.")
        if health.get("status") not in {"ok", "healthy"}:
            return die("/api/health did not report healthy status.")

        # Allowed production CORS
        r = client.options(
            "api/auth/login",
            headers={
                "Origin": allowed_origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        if r.status_code not in {200, 204}:
            return die(f"Allowed-origin CORS preflight returned HTTP {r.status_code}.")
        if r.headers.get("access-control-allow-origin") != allowed_origin:
            return die("Allowed-origin CORS response did not match configured origin.")
        if r.headers.get("access-control-allow-credentials", "").lower() != "true":
            return die("Allowed-origin CORS is missing credential support.")

        # Blocked CORS must not be reflected
        r = client.options(
            "api/auth/login",
            headers={
                "Origin": blocked_origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        if r.headers.get("access-control-allow-origin") == blocked_origin:
            return die("Blocked CORS origin was incorrectly allowed.")

        # Unauthenticated search must be rejected immediately.
        payload = {"state": "TX", "limit": 1}
        r = client.post("api/search", json=payload)
        if r.status_code not in {401, 403}:
            return die(f"Unauthenticated search returned HTTP {r.status_code}; expected 401/403.")

        # Registration + login
        r = client.post("api/auth/register", json={"email": email, "password": password})
        if r.status_code not in {200, 201}:
            return die(f"Registration returned HTTP {r.status_code}.")
        r = client.post("api/auth/login", json={"email": email, "password": password})
        if r.status_code != 200:
            return die(f"Login returned HTTP {r.status_code}.")

        set_cookies = r.headers.get_list("set-cookie")
        if not set_cookies:
            return die("Login did not set an authentication cookie.")
        auth_cookie = next((x for x in set_cookies if "httponly" in x.lower()), None)
        if not auth_cookie:
            return die("Authentication cookie is missing HttpOnly.")
        cookie_lower = auth_cookie.lower()
        if "secure" not in cookie_lower:
            return die("Authentication cookie is missing Secure.")
        if "samesite=" not in cookie_lower:
            return die("Authentication cookie is missing SameSite.")

        r = client.get("api/auth/me")
        if r.status_code != 200:
            return die(f"/api/auth/me returned HTTP {r.status_code}.")
        me = r.json()
        if str(me.get("email", "")).lower() != email.lower():
            return die("/api/auth/me returned the wrong user.")
        if me.get("subscription_status") in {"active", "trialing"}:
            return die("New smoke user unexpectedly started with paid access.")

        # No free tier: the first authenticated search requires subscription.
        # Logged-in users may use the non-identifying teaser preview.
        r = client.post("api/search/preview", json=payload)
        if r.status_code != 200:
            return die(f"Unsubscribed preview returned HTTP {r.status_code}; expected 200.")
        preview = r.json()
        if preview.get("requires_subscription") is not True:
            return die("Preview did not signal subscription requirement for full details.")
        if "results" in preview:
            return die("Preview exposed detailed property results.")

        r = client.post("api/search", json=payload)
        if r.status_code != 402:
            return die(f"Unsubscribed first search returned HTTP {r.status_code}; expected 402.")
        detail = r.json().get("detail", {})
        if not isinstance(detail, dict) or detail.get("code") != "SUBSCRIPTION_REQUIRED":
            return die("First authenticated search did not return SUBSCRIPTION_REQUIRED.")

    print("POST-DEPLOYMENT SMOKE TESTS PASSED")
    print("Checks: startup, CORS, authentication, teaser preview, detailed-result subscription gate")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
