"""Live-mode contracts with synthetic Stripe responses; never sends real payments."""

import copy
import hashlib
import hmac
import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import SecretStr
from sqlalchemy import func, select
from test_admin_billing import owner_and_user
from test_feedback import ACCEPT

from landwolf import billing, feedback
from landwolf.config import Settings
from landwolf.db import (
    AccountEmail,
    BillingEvent,
    FeedbackAudit,
)

ORIGIN = {"Origin": "http://testserver", "X-LandWolf-Client": "web"}
KEY = "sk_" + "live_" + "synthetic_fixture_not_a_secret"
SIGNING = "whsec_" + "synthetic_fixture_not_a_secret"


def login(client, email):
    response = client.post(
        "/api/auth/login",
        headers=ORIGIN,
        json={"email": email, "password": "Test-only passphrase 847!"},
    )
    assert response.status_code == 200
    return {**ORIGIN, "X-CSRF-Token": response.json()["csrf"]}


class FakeStripe:
    def __init__(self):
        self.calls = []
        self.rows = []
        self.sessions = {}
        self.fail = False
        self.lose_checkout_response = False
        self.customer_creations = 0
        self.checkout_creations = 0
        self.bad_price = False

    def call(self, api, method, path, fields=None, *, idempotency_key=None):
        if self.fail:
            raise billing.unavailable()
        self.calls.append((method, path, fields, idempotency_key))
        if path == "/account":
            return {"id": "acct_fixture", "charges_enabled": True}
        if path.startswith("/prices/"):
            monthly = path.endswith("price_monthly")
            return {
                "livemode": True,
                "active": True,
                "type": "one_time" if self.bad_price else "recurring",
                "currency": "usd",
                "unit_amount": 2900 if monthly else 29900,
                "recurring": {"interval": "month" if monthly else "year", "interval_count": 1},
            }
        if path.startswith("/billing_portal/configurations/"):
            return {
                "livemode": True,
                "active": True,
                "features": {"subscription_cancel": {"enabled": True, "mode": "at_period_end"}},
            }
        if path == "/customers":
            self.customer_creations += 1
            return {"id": "cus_fixture", "livemode": True}
        if path == "/subscriptions":
            return {"data": copy.deepcopy(self.rows), "has_more": False}
        if path == "/checkout/sessions":
            if idempotency_key not in self.sessions:
                self.checkout_creations += 1
                self.sessions[idempotency_key] = {
                    "id": f"cs_live_fixture{self.checkout_creations}",
                    "livemode": True,
                    "mode": "subscription",
                    "status": "open",
                    "customer": fields["customer"],
                    "client_reference_id": fields["client_reference_id"],
                    "url": "https://checkout.stripe.com/c/pay/cs_live_fixture",
                }
            if self.lose_checkout_response:
                self.lose_checkout_response = False
                raise billing.unavailable()
            return copy.deepcopy(self.sessions[idempotency_key])
        if path.startswith("/checkout/sessions/"):
            sid = path.split("/")[3]
            value = next(s for s in self.sessions.values() if s["id"] == sid)
            if path.endswith("/expire"):
                value["status"] = "expired"
            return copy.deepcopy(value)
        if path == "/billing_portal/sessions":
            return {"url": "https://billing.stripe.com/p/session/fixture"}
        raise AssertionError((method, path))


@pytest.fixture
def paid_app(client, monkeypatch):
    owner, user, owner_headers = owner_and_user(client)
    client.post("/api/auth/logout", headers=owner_headers, json={})
    headers = login(client, user.email)
    settings = client.app.state.settings
    settings.payments_enabled = True
    settings.stripe_secret_key = SecretStr(KEY)
    settings.stripe_webhook_secret = SecretStr(SIGNING)
    settings.stripe_account_id = "acct_fixture"
    settings.stripe_monthly_price_id = "price_monthly"
    settings.stripe_annual_price_id = "price_annual"
    settings.stripe_portal_configuration_id = "bpc_fixture"
    fake = FakeStripe()
    monkeypatch.setattr(
        billing.StripeAPI, "call", lambda api, *args, **kwargs: fake.call(api, *args, **kwargs)
    )
    return client, owner, user, headers, fake


def buy(client, headers, plan="monthly"):
    return client.post(
        "/api/billing/checkout",
        headers=headers,
        json={"plan": plan, "accepted_recurring_terms": True},
    )


def subscription(user, state="active", **changes):
    return {
        "id": "sub_fixture",
        "livemode": True,
        "customer": "cus_fixture",
        "status": state,
        "collection_method": "charge_automatically",
        "cancel_at_period_end": False,
        "metadata": {"app": "landwolf", "account_id": user.id},
        "items": {
            "has_more": False,
            "data": [
                {
                    "price": {"id": "price_monthly"},
                    "quantity": 1,
                    "current_period_end": int(time.time()) + 3600,
                }
            ],
        },
        **changes,
    }


def event_request(client, event_id="evt_fixture", *, live=True, stamp=None, corrupt=False):
    payload = json.dumps(
        {
            "id": event_id,
            "type": "customer.subscription.updated",
            "livemode": live,
            "data": {"object": {"customer": "cus_fixture"}},
        }
    ).encode()
    stamp = int(time.time()) if stamp is None else stamp
    signature = hmac.new(
        SIGNING.encode(), str(stamp).encode() + b"." + payload, hashlib.sha256
    ).hexdigest()
    return client.post(
        "/api/billing/webhook",
        content=payload + (b" " if corrupt else b""),
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": f"t={stamp},v1={signature}",
        },
    )


def test_unpaid_accounts_are_gated_but_can_recover_and_manage_saved_hunts(paid_app):
    client, _, _, headers, fake = paid_app
    for path in [
        "/api/sources",
        "/api/properties/fixture",
        "/api/hunts/fixture/matches",
        "/api/hunts/fixture/events",
    ]:
        assert client.get(path).status_code == 402
    assert client.post("/api/search", headers=headers, json={}).status_code == 402
    assert client.get("/api/hunts").status_code == 200
    assert client.get("/api/session").json()["billing"]["allowed"] is False
    assert client.get("/api/feedback").json()["access_allowed"] is False
    assert fake.calls == []
    assert client.get("/api/health").json()["payments_enabled"] is True


def test_checkout_is_live_bounded_and_never_authorizes_without_payment(paid_app):
    client, _, user, headers, fake = paid_app
    assert buy(client, headers).status_code == 200
    assert buy(client, headers).status_code == 200
    assert fake.customer_creations == 1 and fake.checkout_creations == 1
    params = next(c[2] for c in fake.calls if c[:2] == ("POST", "/checkout/sessions"))
    assert params["line_items[0][price]"] == "price_monthly"
    assert params["client_reference_id"] == user.id
    assert params["subscription_data[metadata][account_id]"] == user.id
    assert not any(key.startswith("payment_method_types") for key in params)
    assert params["success_url"] == "http://testserver/?billing=return"
    assert not any("trial" in key for key in params)
    assert client.get("/api/billing/status").json()["allowed"] is False


def test_checkout_recovers_a_lost_response_with_one_idempotent_attempt(paid_app):
    client, _, _, headers, fake = paid_app
    fake.lose_checkout_response = True
    assert buy(client, headers).status_code == 503
    assert buy(client, headers).status_code == 200
    assert fake.checkout_creations == 1
    requests = [c for c in fake.calls if c[:2] == ("POST", "/checkout/sessions")]
    assert requests[0][2:] == requests[1][2:]


def test_parallel_checkout_is_single_customer_and_session(paid_app):
    client, _, _, headers, fake = paid_app
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: buy(client, headers), range(2)))
    assert [r.status_code for r in responses] == [200, 200]
    assert fake.customer_creations == fake.checkout_creations == 1


def test_plan_switch_expires_previous_checkout(paid_app):
    client, _, _, headers, fake = paid_app
    assert buy(client, headers).status_code == 200
    assert buy(client, headers, "annual").status_code == 200
    assert fake.checkout_creations == 2
    assert any(c[1].endswith("/expire") for c in fake.calls)
    assert list(fake.sessions.values())[0]["status"] == "expired"


def test_checkout_requires_csrf_consent_and_server_selected_price(paid_app):
    client, _, _, headers, fake = paid_app
    assert buy(client, {}).status_code == 403
    for body in [
        {"plan": "monthly", "accepted_recurring_terms": False},
        {"plan": "annual"},
        {"plan": "free", "accepted_recurring_terms": True},
        {"plan": "monthly", "accepted_recurring_terms": True, "price": "price_other"},
        {"plan": "monthly", "accepted_recurring_terms": True, "customer": "cus_other"},
    ]:
        assert client.post("/api/billing/checkout", headers=headers, json=body).status_code == 422
    assert fake.checkout_creations == 0


def test_signed_webhook_paid_access_duplicate_and_out_of_order(paid_app):
    client, _, user, headers, fake = paid_app
    assert buy(client, headers).status_code == 200
    fake.rows = [subscription(user, cancel_at_period_end=True)]
    assert event_request(client).status_code == 200
    current = client.get("/api/billing/status").json()
    assert current["allowed"] and current["cancel_at_period_end"]
    assert client.post("/api/search", headers=headers, json={}).status_code == 200
    fake.fail = True
    assert event_request(client).status_code == 200
    fake.fail = False
    fake.rows = [subscription(user, "canceled")]
    assert event_request(client, "evt_old_delayed").status_code == 200
    assert client.get("/api/billing/status").json()["allowed"] is False
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(BillingEvent)) == 2


@pytest.mark.parametrize(
    "state",
    ["incomplete", "incomplete_expired", "past_due", "unpaid", "trialing", "paused", "canceled"],
)
def test_nonpaid_subscription_never_grants_access(paid_app, state):
    client, _, user, headers, fake = paid_app
    assert buy(client, headers).status_code == 200
    fake.rows = [subscription(user, state)]
    assert event_request(client).status_code == 200
    assert not client.get("/api/billing/status").json()["allowed"]


def test_other_account_price_and_invoice_only_active_are_not_entitlements(paid_app):
    client, _, user, headers, fake = paid_app
    assert buy(client, headers).status_code == 200
    for i, row in enumerate(
        [
            subscription(user, metadata={"app": "landwolf", "account_id": "someone-else"}),
            subscription(user, collection_method="send_invoice"),
            subscription(user, pause_collection={"behavior": "void"}),
            subscription(
                user,
                items={
                    "has_more": False,
                    "data": [
                        {
                            "price": {"id": "price_other"},
                            "quantity": 1,
                            "current_period_end": 9999999999,
                        }
                    ],
                },
            ),
        ]
    ):
        fake.rows = [row]
        assert event_request(client, f"evt_invalid{i}").status_code == 200
        assert not client.get("/api/billing/status").json()["allowed"]


def test_invalid_or_test_webhooks_do_not_change_state(paid_app):
    client, _, _, _, fake = paid_app
    assert event_request(client, live=False).status_code == 400
    assert event_request(client, stamp=int(time.time()) - 301).status_code == 400
    assert event_request(client, corrupt=True).status_code == 400
    assert client.post("/api/billing/webhook", content=b"{}").status_code == 400
    assert fake.calls == []


def test_portal_never_uses_a_customer_supplied_by_browser(paid_app):
    client, _, _, headers, fake = paid_app
    assert client.post("/api/billing/portal", headers=headers, json={}).status_code == 404
    assert buy(client, headers).status_code == 200
    result = client.post("/api/billing/portal", headers=headers, json={"customer": "cus_victim"})
    assert result.status_code == 200
    call = next(c for c in fake.calls if c[1] == "/billing_portal/sessions")
    assert call[2]["customer"] == "cus_fixture"
    assert call[2]["configuration"] == "bpc_fixture"


def test_owner_and_comp_are_exempt_even_during_stripe_outage(paid_app):
    client, _, user, _, fake = paid_app
    headers = login(client, "owner@example.com")
    assert client.get("/api/billing/status").json()["reason"] == "owner"
    assert buy(client, headers).status_code == 409
    assert (
        client.post(
            f"/api/admin/accounts/{user.id}/complimentary-access",
            headers=headers,
            json={"reason": "Owner authorized fixture"},
        ).status_code
        == 201
    )
    headers = login(client, user.email)
    fake.fail = True
    assert client.get("/api/billing/status").json()["reason"] == "complimentary"
    assert client.post("/api/search", headers=headers, json={}).status_code == 200
    assert buy(client, headers).status_code == 409


def test_marketing_reservation_needs_verified_email_and_acceptance(paid_app):
    client, _, user, headers, fake = paid_app
    client.app.state.settings.pilot_invite_emails = (user.email,)
    assert client.get("/api/billing/status").json()["reason"] == "pilot_verification"
    assert buy(client, headers).status_code == 409
    assert client.get("/api/feedback").json()["state"] == "none"
    with client.app.state.factory() as session, session.begin():
        session.add(AccountEmail(account_id=user.id, verified_at=int(time.time())))
    assert client.get("/api/billing/status").json()["reason"] == "pilot_invited"
    assert client.get("/api/feedback").json()["state"] == "invited"
    accepted = client.post("/api/feedback/accept", headers=headers, json=ACCEPT)
    assert accepted.status_code == 200
    assert client.get("/api/billing/status").json()["reason"] == "pilot"
    assert client.post("/api/search", headers=headers, json={}).status_code == 200
    assert buy(client, headers).status_code == 409
    with client.app.state.factory() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(FeedbackAudit)
                .where(FeedbackAudit.action == "invite")
            )
            == 1
        )
    assert fake.calls == []


def test_expired_pilot_requires_explicit_new_purchase_not_autocharge(paid_app, monkeypatch):
    client, _, user, headers, fake = paid_app
    client.app.state.settings.pilot_invite_emails = (user.email,)
    with client.app.state.factory() as session, session.begin():
        session.add(AccountEmail(account_id=user.id, verified_at=int(time.time())))
    client.get("/api/feedback")
    accepted = client.post("/api/feedback/accept", headers=headers, json=ACCEPT).json()
    monkeypatch.setattr(feedback, "_now", lambda: accepted["expires_at"])
    assert client.post("/api/search", headers=headers, json={}).status_code == 402
    assert client.get("/api/billing/status").json()["reason"] == "subscription_required"
    assert fake.calls == []
    assert buy(client, headers).status_code == 200
    fake.rows = [subscription(user)]
    assert event_request(client).status_code == 200
    assert client.get("/api/feedback").json()["access_allowed"] is True
    assert client.post("/api/search", headers=headers, json={}).status_code == 200


def test_live_setup_checks_owner_account_and_recurring_prices(paid_app):
    client, _, _, _, fake = paid_app
    with client.app.state.factory() as session:
        billing.validate_live_setup(client.app.state.settings, session)
        fake.bad_price = True
        with pytest.raises(RuntimeError, match="approved LandWolf plan"):
            billing.validate_live_setup(client.app.state.settings, session)


def test_settings_reject_sandbox_keys_and_hide_secrets():
    with pytest.raises(ValueError, match="live Stripe"):
        Settings(payments_enabled=True, stripe_secret_key="sk_" + "test_" + "synthetic" * 5)
    settings = Settings(
        payments_enabled=True,
        stripe_secret_key=KEY,
        stripe_webhook_secret=SIGNING,
        stripe_account_id="acct_fixture",
        stripe_monthly_price_id="price_monthly",
        stripe_annual_price_id="price_annual",
        stripe_portal_configuration_id="bpc_fixture",
        owner_account_id="00000000-0000-0000-0000-000000000001",
    )
    assert KEY not in repr(settings) and SIGNING not in repr(settings)


def test_payment_poll_does_not_extend_idle_session(paid_app):
    from landwolf.db import LoginSession

    client, _, _, _, _ = paid_app
    with client.app.state.factory() as session, session.begin():
        for login_session in session.scalars(select(LoginSession)):
            login_session.last_seen -= 30
        before = [(s.token_hash, s.last_seen) for s in session.scalars(select(LoginSession))]
    client.get("/api/billing/status")
    with client.app.state.factory() as session:
        assert [
            (s.token_hash, s.last_seen) for s in session.scalars(select(LoginSession))
        ] == before
