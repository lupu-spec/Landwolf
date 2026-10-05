"""Live-only hosted Stripe Checkout, verified entitlements, and private pilot claims.

Never accept a price, customer ID, email privilege, or payment result from the
browser. Payment pages collect card details on Stripe, not on LandWolf. A return
URL cannot grant access. All entitlement changes use a fresh server-side Stripe
read, serialized per account, so old or duplicate webhooks cannot roll state back.
"""

import hashlib
import hmac
import json
import logging
import re
import time
import uuid
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException
from pydantic import Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from landwolf import admin, feedback, recovery
from landwolf.config import Settings
from landwolf.db import Account, BillingCustomer, BillingEvent, FeedbackAudit, FeedbackEnrollment
from landwolf.schemas import Contract

logger = logging.getLogger(__name__)

API_VERSION = "2026-08-26.dahlia"
SYNC_SECONDS = 300
MAX_STRIPE_BYTES = 1024 * 1024
CHECKOUT_SECONDS = 3600
PLANS: dict[str, dict[str, str | int]] = {
    "monthly": {"amount": 2900, "interval": "month", "label": "$29 / month"},
    "annual": {"amount": 29900, "interval": "year", "label": "$299 / year"},
}
EVENTS = frozenset(
    {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
        "checkout.session.async_payment_failed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "customer.subscription.paused",
        "customer.subscription.resumed",
        "invoice.paid",
        "invoice.payment_failed",
        "invoice.payment_action_required",
    }
)


class CheckoutInput(Contract):
    plan: Literal["monthly", "annual"]
    accepted_recurring_terms: Literal[True] = Field(...)


def now() -> int:
    return int(time.time())


def unavailable() -> HTTPException:
    return HTTPException(
        503, "Billing is temporarily unavailable. Please retry or contact support."
    )


def identifier(value: object, prefix: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(prefix + r"[A-Za-z0-9_]{1,180}", value):
        raise unavailable()
    return value


class StripeAPI:
    """Small, bounded REST adapter; no secret values or upstream payloads in errors."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def call(
        self,
        method: str,
        path: str,
        fields: dict[str, str] | None = None,
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        key = self.settings.stripe_secret_key
        if not self.settings.payments_enabled or key is None:
            raise unavailable()
        headers = {"Stripe-Version": API_VERSION}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        deadline = time.monotonic() + 20
        try:
            with (
                httpx.Client(timeout=10, follow_redirects=False, trust_env=False) as client,
                client.stream(
                    method,
                    "https://api.stripe.com/v1" + path,
                    auth=(key.get_secret_value(), ""),
                    headers=headers,
                    params=fields if method == "GET" else None,
                    data=fields if method == "POST" else None,
                ) as response,
            ):
                if response.status_code < 200 or response.status_code >= 300:
                    # Stripe errors can contain request context. Log only bounded,
                    # control-character-free diagnostic fields; never log the raw body,
                    # request fields, authorization header, or secret key.
                    status = response.status_code
                    code = "unknown"
                    param = "unknown"
                    error_type = "unknown"
                    diagnostic = "unknown"
                    try:
                        error_payload = json.loads(response.read())
                        error = error_payload.get("error", {}) if isinstance(error_payload, dict) else {}
                        if isinstance(error, dict):
                            raw_code = error.get("code")
                            raw_param = error.get("param")
                            raw_type = error.get("type")
                            raw_message = error.get("message")
                            if isinstance(raw_code, str) and len(raw_code) <= 80:
                                code = raw_code
                            if isinstance(raw_param, str) and len(raw_param) <= 120:
                                param = raw_param
                            if isinstance(raw_type, str) and len(raw_type) <= 80:
                                error_type = raw_type
                            if isinstance(raw_message, str):
                                clean = "".join(
                                    ch if ch.isprintable() and ch not in "\r\n" else " "
                                    for ch in raw_message
                                )
                                diagnostic = clean[:240]
                    except (ValueError, httpx.HTTPError):
                        pass
                    logger.warning(
                        "Stripe API request rejected: method=%s path=%s status=%s code=%s param=%s type=%s diagnostic=%s",
                        method,
                        path,
                        status,
                        code,
                        param,
                        error_type,
                        diagnostic,
                    )
                    raise unavailable()
                chunks = bytearray()
                for chunk in response.iter_bytes():
                    if time.monotonic() > deadline:
                        raise unavailable()
                    chunks.extend(chunk)
                    if len(chunks) > MAX_STRIPE_BYTES:
                        raise unavailable()
            data: Any = json.loads(chunks)
            if not isinstance(data, dict):
                raise unavailable()
            return data
        except (httpx.HTTPError, ValueError) as exc:
            raise unavailable() from exc


def price_id(settings: Settings, plan: str) -> str:
    value = (
        settings.stripe_monthly_price_id if plan == "monthly" else settings.stripe_annual_price_id
    )
    return identifier(value, "price_")


def validate_live_setup(settings: Settings, session: Session) -> None:
    """Fail deployment before opening checkout on an incorrect account or price."""
    if not settings.payments_enabled:
        return
    if session.get(Account, settings.owner_account_id) is None:
        raise RuntimeError("Configured owner account does not exist; billing startup refused")
    api = StripeAPI(settings)
    account = api.call("GET", "/account")
    if (
        account.get("id") != settings.stripe_account_id
        or account.get("charges_enabled") is not True
    ):
        raise RuntimeError("Stripe account is not the configured charge-enabled live account")
    for plan, expected in PLANS.items():
        price = api.call("GET", "/prices/" + price_id(settings, plan))
        recurring = price.get("recurring") or {}
        if (
            price.get("livemode") is not True
            or price.get("active") is not True
            or price.get("type") != "recurring"
            or price.get("currency") != "usd"
            or price.get("unit_amount") != expected["amount"]
            or recurring.get("interval") != expected["interval"]
            or recurring.get("interval_count") != 1
        ):
            raise RuntimeError("Live Stripe price does not match the approved LandWolf plan")
    portal = api.call(
        "GET",
        "/billing_portal/configurations/"
        + identifier(settings.stripe_portal_configuration_id, "bpc_"),
    )
    features = portal.get("features") or {}
    cancel = features.get("subscription_cancel") or {}
    if (
        portal.get("active") is not True
        or portal.get("livemode") is not True
        or cancel.get("enabled") is not True
        or cancel.get("mode") != "at_period_end"
    ):
        raise RuntimeError("Live Stripe portal must permit cancellation at the paid period end")


def lock_account(session: Session, account_id: str) -> None:
    # A no-op UPDATE is also a write lock in SQLite, unlike SELECT FOR UPDATE.
    # All checkout and Stripe-refresh transactions take this same lock first.
    session.execute(
        update(Account).where(Account.id == account_id).values(created_at=Account.created_at)
    )
    session.expire_all()


def claim_invitation(session: Session, account: Account, settings: Settings) -> None:
    """A private email reservation is not proof of ownership or a started pilot."""
    if (
        account.email.casefold() not in settings.pilot_invite_emails
        or not recovery.verified(session, account.id)
        or not settings.owner_account_id
        or admin.entitlement(session, account, settings)
        or session.get(FeedbackEnrollment, account.id)
    ):
        return
    lock_account(session, account.id)
    if session.get(FeedbackEnrollment, account.id) is None:
        if session.get(Account, settings.owner_account_id) is None:
            session.rollback()
            raise unavailable()
        stamp = now()
        session.add(
            FeedbackEnrollment(
                account_id=account.id,
                invited_by_account_id=settings.owner_account_id,
                invited_at=stamp,
                state="invited",
                terms_version=feedback.TERMS_VERSION,
            )
        )
        session.add(
            FeedbackAudit(
                id=str(uuid.uuid4()),
                actor_account_id=settings.owner_account_id,
                target_account_id=account.id,
                action="invite",
                created_at=stamp,
                reason="Owner-reserved marketing pilot; email ownership verified",
            )
        )
    session.commit()


def subscriptions(api: StripeAPI, customer: BillingCustomer) -> list[dict[str, Any]]:
    result = api.call(
        "GET",
        "/subscriptions",
        {
            "customer": identifier(customer.customer_id, "cus_"),
            "status": "all",
            "limit": "100",
        },
    )
    rows = result.get("data")
    # Never authorize based on a truncated subscription inventory.
    if result.get("has_more") is not False or not isinstance(rows, list) or len(rows) > 100:
        raise unavailable()
    for row in rows:
        if not isinstance(row, dict) or row.get("livemode") is not True:
            raise unavailable()
        if row.get("customer") != customer.customer_id:
            raise unavailable()
    return rows


def store_subscriptions(
    customer: BillingCustomer,
    rows: list[dict[str, Any]],
    settings: Settings,
) -> None:
    customer.paid_until = 0
    customer.subscription_id = None
    customer.subscription_status = "none"
    customer.cancel_at_period_end = False
    prices = {price_id(settings, plan) for plan in PLANS}
    for row in rows:
        metadata = row.get("metadata") or {}
        items = row.get("items") or {}
        if not isinstance(metadata, dict) or not isinstance(items, dict):
            raise unavailable()
        data = items.get("data") or []
        if not isinstance(data, list):
            raise unavailable()
        if (
            metadata.get("app") != "landwolf"
            or metadata.get("account_id") != customer.account_id
            or items.get("has_more") is not False
            or len(data) != 1
        ):
            continue
        item = data[0]
        if not isinstance(item, dict):
            raise unavailable()
        price = item.get("price") or {}
        if not isinstance(price, dict):
            raise unavailable()
        if price.get("id") not in prices or item.get("quantity") != 1:
            continue
        state = row.get("status")
        if state not in {"active", "past_due", "unpaid", "incomplete", "trialing", "paused"}:
            continue
        period_end = item.get("current_period_end")
        if not isinstance(period_end, int) or isinstance(period_end, bool):
            period_end = 0
        # API version is pinned: the billing period belongs to the subscription item.
        paid = (
            state == "active"
            and row.get("collection_method") == "charge_automatically"
            and not row.get("pause_collection")
            and period_end > now()
        )
        if not customer.subscription_id or (paid and period_end > customer.paid_until):
            customer.subscription_id = identifier(row.get("id"), "sub_")
            customer.subscription_status = str(state)
            customer.cancel_at_period_end = row.get("cancel_at_period_end") is True
        if paid:
            customer.paid_until = max(customer.paid_until, period_end)
    customer.synced_at = now()


def refresh_customer(
    session: Session,
    account: Account,
    settings: Settings,
    *,
    force: bool = False,
) -> BillingCustomer | None:
    customer = session.get(BillingCustomer, account.id)
    if customer is None:
        return None
    expired_active = customer.subscription_status == "active" and customer.paid_until <= now()
    if not force and not expired_active and customer.synced_at > now() - SYNC_SECONDS:
        return customer
    lock_account(session, account.id)
    customer = session.get(BillingCustomer, account.id)
    if customer is None:
        session.rollback()
        return None
    # Recheck after obtaining the lock: another request may have just refreshed it.
    if force or expired_active or customer.synced_at <= now() - SYNC_SECONDS:
        rows = subscriptions(StripeAPI(settings), customer)
        store_subscriptions(customer, rows, settings)
    session.commit()
    return customer


def access(session: Session, account: Account, settings: Settings) -> dict[str, Any]:
    override = admin.entitlement(session, account, settings)
    pilot = feedback.status(session, account, settings=settings)
    customer = session.get(BillingCustomer, account.id)
    result: dict[str, Any] = {
        "enabled": settings.payments_enabled,
        "livemode": settings.payments_enabled,
        "allowed": True,
        "reason": override or "payments_disabled",
        "paid_until": None,
        "subscription_status": "none",
        "cancel_at_period_end": False,
        "has_customer": customer is not None,
        "pilot_reserved": account.email.casefold() in settings.pilot_invite_emails,
        "pilot_state": pilot["state"],
        "plans": [{"id": key, "currency": "usd", **value} for key, value in PLANS.items()],
    }
    if not settings.payments_enabled:
        result["allowed"] = pilot["access_allowed"]
        return result
    if override:
        return result
    # An eligible pilot never depends on Stripe availability and never needs a card.
    if pilot["state"] == "active" and pilot["access_allowed"]:
        result["reason"] = "pilot"
        return result
    customer = refresh_customer(session, account, settings)
    if customer:
        result.update(
            {
                "paid_until": customer.paid_until or None,
                "subscription_status": customer.subscription_status,
                "cancel_at_period_end": customer.cancel_at_period_end,
            }
        )
        if customer.paid_until > now() and customer.subscription_status == "active":
            result["reason"] = "subscription"
            return result
    result.update(
        allowed=False,
        reason=(
            "feedback_required"
            if pilot["state"] == "feedback_required"
            else "pilot_invited"
            if pilot["state"] == "invited"
            else "pilot_verification"
            if result["pilot_reserved"] and pilot["state"] == "none"
            else "subscription_required"
        ),
    )
    return result


def require_access(session: Session, account: Account, settings: Settings) -> None:
    if not settings.payments_enabled:
        feedback.require_access(session, account, settings)
        return
    result = access(session, account, settings)
    if result["allowed"]:
        return
    if result["reason"] == "feedback_required":
        feedback.require_access(session, account, settings)
    raise HTTPException(
        402,
        {
            "code": "PAYMENT_REQUIRED",
            "message": "Choose a subscription or activate an eligible pilot.",
            "reason": result["reason"],
        },
    )


def trusted_url(value: object, host: str) -> str:
    if not isinstance(value, str):
        raise unavailable()
    url = urlsplit(value)
    if url.scheme != "https" or url.hostname != host or url.username or url.password or url.port:
        raise unavailable()
    return value


def customer_for_checkout(
    session: Session, account: Account, settings: Settings
) -> BillingCustomer:
    lock_account(session, account.id)
    customer = session.get(BillingCustomer, account.id)
    if customer is None:
        result = StripeAPI(settings).call(
            "POST",
            "/customers",
            {
                "email": account.email,
                "metadata[app]": "landwolf",
                "metadata[account_id]": account.id,
            },
            idempotency_key=f"landwolf-live-customer-{account.id}",
        )
        if result.get("livemode") is not True:
            raise unavailable()
        customer = BillingCustomer(
            account_id=account.id, customer_id=identifier(result.get("id"), "cus_")
        )
        session.add(customer)
        session.flush()
    session.commit()
    return customer


def checkout_fields(customer: BillingCustomer, settings: Settings) -> dict[str, str]:
    if not customer.checkout_started_at or customer.checkout_plan not in PLANS:
        raise unavailable()
    return {
        "mode": "subscription",
        "customer": customer.customer_id,
        "client_reference_id": customer.account_id,
        "line_items[0][price]": price_id(settings, customer.checkout_plan),
        "line_items[0][quantity]": "1",
        "metadata[app]": "landwolf",
        "metadata[account_id]": customer.account_id,
        "subscription_data[metadata][app]": "landwolf",
        "subscription_data[metadata][account_id]": customer.account_id,
        "subscription_data[metadata][terms_version]": "subscription-v1",
        "metadata[terms_version]": "subscription-v1",
        "success_url": settings.public_origin + "/?billing=return",
        "cancel_url": settings.public_origin + "/?billing=cancelled",
        "expires_at": str(customer.checkout_started_at + CHECKOUT_SECONDS),
    }


def resolve_checkout(
    api: StripeAPI, customer: BillingCustomer, settings: Settings
) -> dict[str, Any]:
    if customer.checkout_id:
        result = api.call(
            "GET", "/checkout/sessions/" + identifier(customer.checkout_id, "cs_live_")
        )
    else:
        result = api.call(
            "POST",
            "/checkout/sessions",
            checkout_fields(customer, settings),
            idempotency_key=f"landwolf-live-checkout-{customer.checkout_attempt}",
        )
    if (
        result.get("livemode") is not True
        or result.get("customer") != customer.customer_id
        or result.get("client_reference_id") != customer.account_id
        or result.get("mode") != "subscription"
    ):
        raise unavailable()
    customer.checkout_id = identifier(result.get("id"), "cs_live_")
    return result


def checkout(
    session: Session,
    account: Account,
    settings: Settings,
    body: CheckoutInput,
) -> dict[str, str]:
    if not settings.payments_enabled:
        raise HTTPException(404, "Payments are disabled")
    current = access(session, account, settings)
    if current["allowed"]:
        raise HTTPException(409, "You already have access; no payment is required")
    if current["reason"] in {"pilot_invited", "pilot_verification"}:
        raise HTTPException(
            409, "Activate your reserved pilot or contact support; no payment is required"
        )
    customer = customer_for_checkout(session, account, settings)
    api = StripeAPI(settings)
    lock_account(session, account.id)
    rows = subscriptions(api, customer)
    # Refuse a second subscription, including any unrecognized plan on this customer.
    if any(row.get("status") not in {"canceled", "incomplete_expired"} for row in rows):
        session.rollback()
        raise HTTPException(409, "An existing subscription needs attention. Open Manage billing.")
    if (
        customer.checkout_attempt
        and customer.checkout_started_at
        and customer.checkout_started_at + CHECKOUT_SECONDS <= now()
        and not customer.checkout_id
    ):
        # An unresolved expired attempt can no longer charge. The fresh list above
        # already ruled out any nonterminal subscription it might have created.
        customer.checkout_attempt = None
    if customer.checkout_attempt:
        result = resolve_checkout(api, customer, settings)
        if result.get("status") == "complete" and not any(
            row.get("id") == result.get("subscription") for row in rows
        ):
            session.commit()
            raise HTTPException(
                409, "Payment is processing. Use Check payment status; do not pay again."
            )
        if result.get("status") == "open" and customer.checkout_plan == body.plan:
            session.commit()
            return {"url": trusted_url(result.get("url"), "checkout.stripe.com")}
        if result.get("status") == "open":
            api.call(
                "POST",
                "/checkout/sessions/" + identifier(customer.checkout_id, "cs_live_") + "/expire",
                {},
                idempotency_key=f"landwolf-expire-{customer.checkout_attempt}",
            )
    customer.checkout_attempt = str(uuid.uuid4())
    customer.checkout_plan = body.plan
    customer.checkout_started_at = now()
    customer.checkout_id = None
    # Persist the idempotency identity before the network call; a lost response
    # can be retried with the exact same parameters, even in a different process.
    session.commit()
    lock_account(session, account.id)
    if customer.checkout_plan != body.plan:
        session.rollback()
        raise HTTPException(409, "Your checkout plan changed in another window. Select it again.")
    result = resolve_checkout(api, customer, settings)
    session.commit()
    return {"url": trusted_url(result.get("url"), "checkout.stripe.com")}


def portal(session: Session, account: Account, settings: Settings) -> dict[str, str]:
    customer = session.get(BillingCustomer, account.id)
    if not settings.payments_enabled or customer is None:
        raise HTTPException(404, "No paid billing account exists")
    result = StripeAPI(settings).call(
        "POST",
        "/billing_portal/sessions",
        {
            "customer": identifier(customer.customer_id, "cus_"),
            "configuration": identifier(settings.stripe_portal_configuration_id, "bpc_"),
            "return_url": settings.public_origin + "/?billing=return",
        },
    )
    return {"url": trusted_url(result.get("url"), "billing.stripe.com")}


def verified_event(payload: bytes, signature: str, settings: Settings) -> dict[str, Any]:
    secret = settings.stripe_webhook_secret
    if not settings.payments_enabled or secret is None:
        raise HTTPException(503, "Billing webhook is not configured")
    if len(signature) > 4096:
        raise HTTPException(400, "Invalid webhook signature")
    try:
        parts = [part.split("=", 1) for part in signature.split(",")]
        timestamps = [value for name, value in parts if name == "t"]
        if len(timestamps) != 1:
            raise ValueError("Timestamp required")
        timestamp = int(timestamps[0])
        expected = hmac.new(
            secret.get_secret_value().encode(),
            str(timestamp).encode() + b"." + payload,
            hashlib.sha256,
        ).hexdigest()
        valid = any(
            name == "v1" and len(value) == 64 and hmac.compare_digest(expected, value)
            for name, value in parts
        )
        if not valid or abs(now() - timestamp) > 300:
            raise ValueError("Signature rejected")
        event: Any = json.loads(payload)
        if (
            not isinstance(event, dict)
            or event.get("livemode") is not True
            or not isinstance(event.get("type"), str)
        ):
            raise ValueError("Only live events are accepted")
        return event
    except (ValueError, TypeError, UnicodeError) as exc:
        raise HTTPException(400, "Invalid webhook signature or event") from exc


def webhook(session: Session, event: dict[str, Any], settings: Settings) -> dict[str, bool]:
    kind = event.get("type")
    if kind not in EVENTS:
        return {"received": True}
    event_id = identifier(event.get("id"), "evt_")
    data = event.get("data") or {}
    if not isinstance(data, dict) or not isinstance(data.get("object"), dict):
        raise HTTPException(400, "Invalid webhook object")
    obj = data["object"]
    customer_id = obj.get("customer")
    # Unrelated legacy or other-product customers cannot alter LandWolf accounts.
    if not isinstance(customer_id, str):
        return {"received": True}
    customer = session.scalar(
        select(BillingCustomer).where(BillingCustomer.customer_id == customer_id)
    )
    if customer is None:
        return {"received": True}
    lock_account(session, customer.account_id)
    if session.get(BillingEvent, event_id):
        session.rollback()
        return {"received": True}
    rows = subscriptions(StripeAPI(settings), customer)
    store_subscriptions(customer, rows, settings)
    session.add(
        BillingEvent(
            event_id=event_id,
            account_id=customer.account_id,
            event_type=str(kind),
            processed_at=now(),
        )
    )
    session.commit()
    return {"received": True}
