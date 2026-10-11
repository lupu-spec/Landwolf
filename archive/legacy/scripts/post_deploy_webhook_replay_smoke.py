#!/usr/bin/env python3
"""
Stripe webhook replay/order smoke tests.

Verifies live handling of:
- checkout.session.completed
- customer.subscription.updated
- customer.subscription.deleted

Also verifies:
- exact duplicate delivery is idempotent;
- duplicate events do not corrupt state;
- out-of-order older events do not resurrect a revoked subscription;
- state transitions remain monotonic according to event creation time.

Required environment:
  SMOKE_BASE_URL
  STRIPE_WEBHOOK_SECRET
  STRIPE_PRICE_ID

Optional:
  SMOKE_TIMEOUT_SECONDS
  SMOKE_TEST_EMAIL_DOMAIN
  SMOKE_TEST_PASSWORD
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import uuid

import httpx

def fail(message: str) -> int:
    print(f"WEBHOOK REPLAY SMOKE FAILED: {message}", file=sys.stderr)
    return 1

def need(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable {name}")
    return value

def stripe_signature(payload: bytes, secret: str, timestamp: int | None = None) -> str:
    ts = int(timestamp or time.time())
    signed_payload = f"{ts}.".encode() + payload
    digest = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"

def send_event(client: httpx.Client, secret: str, event: dict) -> httpx.Response:
    payload = json.dumps(event, separators=(",", ":")).encode()
    return client.post(
        "api/billing/webhook",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": stripe_signature(payload, secret),
        },
    )

def expect_status(client: httpx.Client, expected: set[str]) -> tuple[bool, str]:
    r = client.get("api/auth/me")
    if r.status_code != 200:
        return False, f"/api/auth/me returned HTTP {r.status_code}"
    status = str(r.json().get("subscription_status") or "")
    if status not in expected:
        return False, f"subscription_status={status!r}, expected one of {sorted(expected)}"
    return True, status

def main() -> int:
    try:
        base_url = need("SMOKE_BASE_URL").rstrip("/") + "/"
        webhook_secret = need("STRIPE_WEBHOOK_SECRET")
        price_id = need("STRIPE_PRICE_ID")
        timeout = float(os.getenv("SMOKE_TIMEOUT_SECONDS", "15"))
    except Exception as exc:
        return fail(str(exc))

    if not base_url.startswith("https://"):
        return fail("SMOKE_BASE_URL must use HTTPS.")
    if not webhook_secret.startswith("whsec_"):
        return fail("STRIPE_WEBHOOK_SECRET is malformed.")
    if not price_id.startswith("price_"):
        return fail("STRIPE_PRICE_ID is malformed.")

    password = os.getenv("SMOKE_TEST_PASSWORD") or secrets.token_urlsafe(24) + "Aa1!"
    domain = os.getenv("SMOKE_TEST_EMAIL_DOMAIN", "example.invalid").strip()
    email = f"replay-smoke-{uuid.uuid4().hex}@{domain}"

    with httpx.Client(
        base_url=base_url,
        timeout=timeout,
        follow_redirects=False,
        headers={"User-Agent": "property-intelligence-webhook-replay-smoke/1.0"},
    ) as client:
        # Register/login and discover user id.
        r = client.post("api/auth/register", json={"email": email, "password": password})
        if r.status_code not in {200, 201}:
            return fail(f"Registration returned HTTP {r.status_code}.")
        r = client.post("api/auth/login", json={"email": email, "password": password})
        if r.status_code != 200:
            return fail(f"Login returned HTTP {r.status_code}.")
        r = client.get("api/auth/me")
        if r.status_code != 200:
            return fail("Could not read authenticated user.")
        me = r.json()
        user_id = str(me.get("id") or me.get("user_id") or "")
        if not user_id:
            return fail("User id unavailable from /api/auth/me.")

        customer_id = "cus_smoke_" + uuid.uuid4().hex[:14]
        subscription_id = "sub_smoke_" + uuid.uuid4().hex[:14]
        now = int(time.time())

        checkout_event = {
            "id": "evt_smoke_checkout_" + uuid.uuid4().hex,
            "object": "event",
            "created": now,
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_smoke_" + uuid.uuid4().hex[:14],
                    "object": "checkout.session",
                    "customer": customer_id,
                    "subscription": subscription_id,
                    "mode": "subscription",
                    "payment_status": "paid",
                    "metadata": {
                        "user_id": user_id,
                        "smoke_test": "true"
                    }
                }
            }
        }

        active_event = {
            "id": "evt_smoke_active_" + uuid.uuid4().hex,
            "object": "event",
            "created": now + 10,
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": subscription_id,
                    "object": "subscription",
                    "customer": customer_id,
                    "status": "active",
                    "metadata": {
                        "user_id": user_id,
                        "smoke_test": "true"
                    },
                    "items": {"data": [{"price": {"id": price_id}}]}
                }
            }
        }

        deleted_event = {
            "id": "evt_smoke_deleted_" + uuid.uuid4().hex,
            "object": "event",
            "created": now + 20,
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": subscription_id,
                    "object": "subscription",
                    "customer": customer_id,
                    "status": "canceled",
                    "metadata": {
                        "user_id": user_id,
                        "smoke_test": "true"
                    },
                    "items": {"data": [{"price": {"id": price_id}}]}
                }
            }
        }

        # 1. checkout.session.completed accepted.
        r = send_event(client, webhook_secret, checkout_event)
        if r.status_code not in {200, 204}:
            return fail(f"checkout.session.completed returned HTTP {r.status_code}.")

        # Replay exact checkout event.
        r = send_event(client, webhook_secret, checkout_event)
        if r.status_code not in {200, 204}:
            return fail(f"Duplicate checkout.session.completed returned HTTP {r.status_code}.")

        # 2. active update accepted and reflected.
        r = send_event(client, webhook_secret, active_event)
        if r.status_code not in {200, 204}:
            return fail(f"customer.subscription.updated returned HTTP {r.status_code}.")
        ok, detail = expect_status(client, {"active", "trialing"})
        if not ok:
            return fail("Active update state transition failed: " + detail)

        # Replay exact active event.
        r = send_event(client, webhook_secret, active_event)
        if r.status_code not in {200, 204}:
            return fail(f"Duplicate customer.subscription.updated returned HTTP {r.status_code}.")
        ok, detail = expect_status(client, {"active", "trialing"})
        if not ok:
            return fail("Duplicate active event corrupted state: " + detail)

        # 3. deleted event revokes access.
        r = send_event(client, webhook_secret, deleted_event)
        if r.status_code not in {200, 204}:
            return fail(f"customer.subscription.deleted returned HTTP {r.status_code}.")
        ok, detail = expect_status(client, {"canceled", "cancelled", "none", "inactive", "unpaid"})
        if not ok:
            return fail("Deleted event state transition failed: " + detail)

        # Replay exact delete event.
        r = send_event(client, webhook_secret, deleted_event)
        if r.status_code not in {200, 204}:
            return fail(f"Duplicate customer.subscription.deleted returned HTTP {r.status_code}.")
        ok, detail = expect_status(client, {"canceled", "cancelled", "none", "inactive", "unpaid"})
        if not ok:
            return fail("Duplicate delete event corrupted state: " + detail)

        # 4. Out-of-order older active update must not resurrect revoked access.
        older_active = dict(active_event)
        older_active["id"] = "evt_smoke_old_active_" + uuid.uuid4().hex
        older_active["created"] = now + 5
        r = send_event(client, webhook_secret, older_active)
        if r.status_code not in {200, 204}:
            return fail(f"Out-of-order older active event returned HTTP {r.status_code}.")
        ok, detail = expect_status(client, {"canceled", "cancelled", "none", "inactive", "unpaid"})
        if not ok:
            return fail("Out-of-order active event resurrected or corrupted revoked state: " + detail)

        # 5. Out-of-order older checkout event must also not resurrect access.
        older_checkout = dict(checkout_event)
        older_checkout["id"] = "evt_smoke_old_checkout_" + uuid.uuid4().hex
        older_checkout["created"] = now - 10
        r = send_event(client, webhook_secret, older_checkout)
        if r.status_code not in {200, 204}:
            return fail(f"Out-of-order checkout event returned HTTP {r.status_code}.")
        ok, detail = expect_status(client, {"canceled", "cancelled", "none", "inactive", "unpaid"})
        if not ok:
            return fail("Out-of-order checkout event resurrected revoked state: " + detail)

    print("STRIPE WEBHOOK REPLAY/ORDER SMOKE TESTS PASSED")
    print("Checks: checkout replay, update replay, delete replay, duplicate safety, out-of-order safety")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
