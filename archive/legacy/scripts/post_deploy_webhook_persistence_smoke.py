#!/usr/bin/env python3
"""
Post-deployment Stripe webhook persistence smoke test.

Verifies:
- Stripe event IDs are persisted exactly once;
- Stripe `created` timestamps are persisted;
- event ledger + subscription state transition are committed together;
- exact duplicate delivery is ignored;
- a newer event wins;
- a unique older event is persisted as `ignored_stale` and cannot overwrite state.

Required:
  SMOKE_BASE_URL
  DATABASE_URL
  STRIPE_WEBHOOK_SECRET
  STRIPE_PRICE_ID
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
import psycopg


def fail(message: str) -> int:
    print(f"WEBHOOK PERSISTENCE SMOKE FAILED: {message}", file=sys.stderr)
    return 1


def need(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable {name}")
    return value


def db_dsn(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def sign(payload: bytes, secret: str) -> str:
    ts = int(time.time())
    digest = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


def send(client: httpx.Client, secret: str, event: dict) -> httpx.Response:
    payload = json.dumps(event, separators=(",", ":")).encode()
    return client.post(
        "api/billing/webhook",
        content=payload,
        headers={"Content-Type": "application/json", "Stripe-Signature": sign(payload, secret)},
    )


def event_row(conn, event_id: str):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT stripe_event_id, event_type, stripe_created, customer_id,
                   subscription_id, processing_result
            FROM subscription_events
            WHERE stripe_event_id = %s
            """,
            (event_id,),
        )
        return cur.fetchone()


def event_count(conn, event_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM subscription_events WHERE stripe_event_id = %s",
            (event_id,),
        )
        return int(cur.fetchone()[0])


def user_state(conn, user_id: str):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT subscription_status, last_stripe_event_id,
                   last_stripe_event_type, last_stripe_event_created
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )
        return cur.fetchone()


def main() -> int:
    try:
        base_url = need("SMOKE_BASE_URL").rstrip("/") + "/"
        database_url = need("DATABASE_URL")
        webhook_secret = need("STRIPE_WEBHOOK_SECRET")
        price_id = need("STRIPE_PRICE_ID")
    except Exception as exc:
        return fail(str(exc))

    if not base_url.startswith("https://"):
        return fail("SMOKE_BASE_URL must use HTTPS.")

    password = secrets.token_urlsafe(24) + "Aa1!"
    domain = os.getenv("SMOKE_TEST_EMAIL_DOMAIN", "example.invalid")
    email = f"persistence-smoke-{uuid.uuid4().hex}@{domain}"
    now = int(time.time())

    with httpx.Client(base_url=base_url, timeout=15, follow_redirects=False) as client, \
         psycopg.connect(db_dsn(database_url), autocommit=True) as conn:

        r = client.post("api/auth/register", json={"email": email, "password": password})
        if r.status_code not in {200, 201}:
            return fail(f"Registration returned HTTP {r.status_code}.")
        r = client.post("api/auth/login", json={"email": email, "password": password})
        if r.status_code != 200:
            return fail(f"Login returned HTTP {r.status_code}.")
        me = client.get("api/auth/me").json()
        user_id = str(me.get("id") or me.get("user_id") or "")
        if not user_id:
            return fail("No user id returned.")

        customer_id = "cus_smoke_" + uuid.uuid4().hex[:14]
        sub_id = "sub_smoke_" + uuid.uuid4().hex[:14]

        active_id = "evt_persist_active_" + uuid.uuid4().hex
        active_created = now + 20
        active = {
            "id": active_id,
            "object": "event",
            "created": active_created,
            "type": "customer.subscription.updated",
            "data": {"object": {
                "id": sub_id, "object": "subscription", "customer": customer_id,
                "status": "active",
                "metadata": {"user_id": user_id, "smoke_test": "true"},
                "items": {"data": [{"price": {"id": price_id}}]},
            }},
        }

        r = send(client, webhook_secret, active)
        if r.status_code not in {200, 204}:
            return fail(f"Active webhook returned HTTP {r.status_code}.")

        row = event_row(conn, active_id)
        state = user_state(conn, user_id)
        if not row:
            return fail("Active Stripe event ID was not persisted.")
        if row[2] != active_created:
            return fail("Stripe created timestamp was not persisted exactly.")
        if row[5] != "applied":
            return fail(f"Active event processing_result={row[5]!r}, expected 'applied'.")
        if not state or state[0] != "active" or state[1] != active_id or state[3] != active_created:
            return fail("Event ledger and subscription state were not committed consistently.")

        # Exact duplicate must remain one row and preserve state.
        r = send(client, webhook_secret, active)
        if r.status_code not in {200, 204}:
            return fail("Duplicate active webhook was not safely accepted.")
        if event_count(conn, active_id) != 1:
            return fail("Duplicate delivery created more than one event ledger row.")
        if user_state(conn, user_id) != state:
            return fail("Duplicate delivery changed subscription state.")

        # Newer deletion must atomically become authoritative.
        delete_id = "evt_persist_delete_" + uuid.uuid4().hex
        delete_created = now + 40
        deleted = {
            "id": delete_id,
            "object": "event",
            "created": delete_created,
            "type": "customer.subscription.deleted",
            "data": {"object": {
                "id": sub_id, "object": "subscription", "customer": customer_id,
                "status": "canceled",
                "metadata": {"user_id": user_id, "smoke_test": "true"},
                "items": {"data": [{"price": {"id": price_id}}]},
            }},
        }
        r = send(client, webhook_secret, deleted)
        if r.status_code not in {200, 204}:
            return fail("Delete webhook failed.")
        drow = event_row(conn, delete_id)
        dstate = user_state(conn, user_id)
        if not drow or drow[2] != delete_created or drow[5] != "applied":
            return fail("Newer delete event was not persisted as applied.")
        if not dstate or dstate[0] != "canceled" or dstate[1] != delete_id or dstate[3] != delete_created:
            return fail("Newer delete event and canceled state were not committed together.")

        # Unique stale event should be recorded for audit but must not overwrite newer state.
        stale_id = "evt_persist_stale_" + uuid.uuid4().hex
        stale_created = now + 30
        stale = {
            "id": stale_id,
            "object": "event",
            "created": stale_created,
            "type": "customer.subscription.updated",
            "data": {"object": {
                "id": sub_id, "object": "subscription", "customer": customer_id,
                "status": "active",
                "metadata": {"user_id": user_id, "smoke_test": "true"},
                "items": {"data": [{"price": {"id": price_id}}]},
            }},
        }
        r = send(client, webhook_secret, stale)
        if r.status_code not in {200, 204}:
            return fail("Stale webhook was not safely accepted.")
        srow = event_row(conn, stale_id)
        if not srow:
            return fail("Unique stale event was not persisted for audit.")
        if srow[2] != stale_created or srow[5] != "ignored_stale":
            return fail("Stale event was not persisted with ignored_stale result.")
        if user_state(conn, user_id) != dstate:
            return fail("Older event overwrote newer subscription state.")

    print("STRIPE WEBHOOK PERSISTENCE SMOKE TESTS PASSED")
    print("Checks: event-id persistence, Stripe timestamps, atomic state, duplicate ignore, stale-event protection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
