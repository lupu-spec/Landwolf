#!/usr/bin/env python3
"""
Live Stripe subscription smoke tests.

This script verifies:
1. checkout session creation for an authenticated user;
2. signed Stripe webhook handling;
3. unsubscribed users are blocked from search immediately;
4. active/trialing subscription enables search and revoked/canceled subscription removes access;
5. duplicate webhook delivery is handled idempotently.

Required environment:
  SMOKE_BASE_URL
  SMOKE_ALLOWED_ORIGIN
  STRIPE_WEBHOOK_SECRET
  STRIPE_PRICE_ID

Optional:
  SMOKE_TIMEOUT_SECONDS
  SMOKE_TEST_EMAIL_DOMAIN
  SMOKE_TEST_PASSWORD

The script never prints passwords, cookies, tokens, or webhook secrets.
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
    print(f"SUBSCRIPTION SMOKE FAILED: {message}", file=sys.stderr)
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

def post_signed_webhook(client: httpx.Client, secret: str, event: dict) -> httpx.Response:
    payload = json.dumps(event, separators=(",", ":")).encode()
    sig = stripe_signature(payload, secret)
    return client.post(
        "api/billing/webhook",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": sig,
        },
    )

def main() -> int:
    try:
        base_url = need("SMOKE_BASE_URL").rstrip("/") + "/"
        allowed_origin = need("SMOKE_ALLOWED_ORIGIN")
        webhook_secret = need("STRIPE_WEBHOOK_SECRET")
        price_id = need("STRIPE_PRICE_ID")
        timeout = float(os.getenv("SMOKE_TIMEOUT_SECONDS", "15"))
    except Exception as exc:
        return fail(str(exc))

    if not base_url.startswith("https://"):
        return fail("SMOKE_BASE_URL must use HTTPS.")
    if not allowed_origin.startswith("https://"):
        return fail("SMOKE_ALLOWED_ORIGIN must use HTTPS.")
    if not webhook_secret.startswith("whsec_"):
        return fail("STRIPE_WEBHOOK_SECRET does not look like a Stripe webhook signing secret.")
    if not price_id.startswith("price_"):
        return fail("STRIPE_PRICE_ID does not look like a Stripe price id.")

    password = os.getenv("SMOKE_TEST_PASSWORD") or secrets.token_urlsafe(24) + "Aa1!"
    domain = os.getenv("SMOKE_TEST_EMAIL_DOMAIN", "example.invalid").strip()
    email = f"stripe-smoke-{uuid.uuid4().hex}@{domain}"
    user_id = None

    with httpx.Client(
        base_url=base_url,
        timeout=timeout,
        follow_redirects=False,
        headers={"User-Agent": "property-intelligence-stripe-smoke/1.0"},
    ) as client:
        # Register and authenticate unique smoke user.
        r = client.post("api/auth/register", json={"email": email, "password": password})
        if r.status_code not in {200, 201}:
            return fail(f"Registration returned HTTP {r.status_code}.")
        r = client.post("api/auth/login", json={"email": email, "password": password})
        if r.status_code != 200:
            return fail(f"Login returned HTTP {r.status_code}.")

        r = client.get("api/auth/me")
        if r.status_code != 200:
            return fail(f"/api/auth/me returned HTTP {r.status_code}.")
        me = r.json()
        user_id = str(me.get("id") or me.get("user_id") or "")
        if not user_id:
            return fail("/api/auth/me did not expose a user id required for webhook targeting.")

        # No free tier: the first search must be blocked before subscription activation.
        payload = {"state": "TX", "limit": 1}
        r = client.post("api/search", json=payload)
        if r.status_code != 402:
            return fail(f"Unsubscribed first search returned HTTP {r.status_code}; expected 402.")
        detail = r.json().get("detail", {})
        if not isinstance(detail, dict) or detail.get("code") != "SUBSCRIPTION_REQUIRED":
            return fail("Unsubscribed first search did not return SUBSCRIPTION_REQUIRED.")

        # Checkout creation should succeed for authenticated user.
        r = client.post("api/billing/checkout")
        if r.status_code not in {200, 201}:
            return fail(f"Checkout creation returned HTTP {r.status_code}.")
        try:
            checkout = r.json()
        except Exception:
            return fail("Checkout creation did not return JSON.")
        checkout_url = checkout.get("url") or checkout.get("checkout_url")
        if not checkout_url or not str(checkout_url).startswith("https://"):
            return fail("Checkout response did not contain an HTTPS checkout URL.")

        # Activate subscription using a signed Stripe webhook event.
        # The app associates subscriptions via user metadata/customer identity.
        event_id = "evt_smoke_active_" + uuid.uuid4().hex
        customer_id = "cus_smoke_" + uuid.uuid4().hex[:14]
        subscription_id = "sub_smoke_" + uuid.uuid4().hex[:14]

        active_event = {
            "id": event_id,
            "object": "event",
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
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": price_id
                                }
                            }
                        ]
                    }
                }
            }
        }

        r = post_signed_webhook(client, webhook_secret, active_event)
        if r.status_code not in {200, 204}:
            return fail(f"Active-subscription webhook returned HTTP {r.status_code}.")

        # Duplicate delivery must not create a second effect or error.
        r_dup = post_signed_webhook(client, webhook_secret, active_event)
        if r_dup.status_code not in {200, 204}:
            return fail(f"Duplicate webhook returned HTTP {r_dup.status_code}; webhook is not idempotent.")

        # Authenticated user should now report paid status.
        r = client.get("api/auth/me")
        if r.status_code != 200:
            return fail("Could not read account after active webhook.")
        me = r.json()
        if me.get("subscription_status") not in {"active", "trialing"}:
            return fail("Active subscription webhook did not unlock the account.")

        # Active subscription must enable search.
        r = client.post("api/search", json=payload)
        if r.status_code != 200:
            return fail(f"Active subscriber search returned HTTP {r.status_code}, expected 200.")

        # Revoke subscription.
        revoked_event = {
            "id": "evt_smoke_revoked_" + uuid.uuid4().hex,
            "object": "event",
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
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": price_id
                                }
                            }
                        ]
                    }
                }
            }
        }

        r = post_signed_webhook(client, webhook_secret, revoked_event)
        if r.status_code not in {200, 204}:
            return fail(f"Revoked-subscription webhook returned HTTP {r.status_code}.")

        r = client.get("api/auth/me")
        if r.status_code != 200:
            return fail("Could not read account after revoked webhook.")
        if r.json().get("subscription_status") in {"active", "trialing"}:
            return fail("Revoked subscription still reports paid status.")

        # Revocation must immediately block search again.
        r = client.post("api/search", json=payload)
        if r.status_code != 402:
            return fail(f"Revoked subscriber search returned HTTP {r.status_code}; expected 402.")
        try:
            body = r.json()
        except Exception:
            return fail("Revoked-access response was not JSON.")
        detail = body.get("detail", body)
        code = detail.get("code") if isinstance(detail, dict) else None
        if code != "SUBSCRIPTION_REQUIRED":
            return fail("Revoked subscription did not restore SUBSCRIPTION_REQUIRED enforcement.")

    print("STRIPE SUBSCRIPTION SMOKE TESTS PASSED")
    print("Checks: checkout, signed webhook, idempotency, active access, revoked access")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
