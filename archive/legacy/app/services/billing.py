import hmac
import stripe
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import SubscriptionEvent, User


PLAN_PRICE_IDS = {
    "monthly": lambda: settings.stripe_monthly_price_id,
    "annual": lambda: settings.stripe_annual_price_id,
}

SUPPORTED_WEBHOOK_EVENTS = {
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_failed",
    "invoice.paid",
}


def configured():
    return bool(
        settings.stripe_api_secret
        and settings.stripe_monthly_price_id
        and settings.stripe_annual_price_id
    )


def price_id_for_plan(plan: str) -> str:
    resolver = PLAN_PRICE_IDS.get(plan)
    if resolver is None:
        raise HTTPException(status_code=400, detail="Invalid subscription plan")
    price_id = resolver()
    if not price_id:
        raise HTTPException(status_code=503, detail="Billing plan is not configured")
    return price_id


def checkout_for_user(db: Session, user: User, plan: str = "monthly") -> str:
    if not configured():
        raise HTTPException(status_code=503, detail="Billing is not configured")

    stripe.api_key = settings.stripe_api_secret
    price_id = price_id_for_plan(plan)

    if not user.stripe_customer_id:
        customer = stripe.Customer.create(email=user.email, metadata={"user_id": user.id})
        user.stripe_customer_id = customer.id
        db.commit()

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=user.stripe_customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=settings.stripe_success_url,
        cancel_url=settings.stripe_cancel_url,
        metadata={"user_id": user.id, "plan": plan},
        subscription_data={"metadata": {"user_id": user.id, "plan": plan}},
    )
    return session.url


def _subscription_id(event_type: str, obj) -> str | None:
    if event_type == "checkout.session.completed":
        return obj.get("subscription")
    return obj.get("id") if str(obj.get("object", "")) == "subscription" else obj.get("subscription")


def _desired_status(event_type: str, obj) -> str | None:
    if event_type == "checkout.session.completed":
        # Never grant entitlement from the Checkout completion alone.
        # Subscription lifecycle events are authoritative for access.
        return None
    if event_type in {"customer.subscription.created", "customer.subscription.updated"}:
        return obj.get("status") or "active"
    if event_type == "customer.subscription.deleted":
        return "canceled"
    return None


def _failure_secret() -> str | None:
    value = settings.webhook_failure_injection_secret
    if value is None:
        return None
    return value.get_secret_value() if hasattr(value, "get_secret_value") else str(value)


def _maybe_inject_failure(requested: str | None, point: str) -> None:
    expected = _failure_secret()
    if not expected or not requested:
        return
    try:
        supplied_secret, supplied_point = requested.split(":", 1)
    except ValueError:
        return
    if hmac.compare_digest(supplied_secret, expected) and supplied_point == point:
        raise RuntimeError(f"Injected webhook transaction failure at {point}")


def process_webhook(db: Session, payload: bytes, signature: str | None, failure_injection: str | None = None):
    """
    Process a Stripe webhook transactionally.

    Invariants:
    - Stripe event IDs are unique and persisted.
    - Stripe `created` timestamps are persisted.
    - Event record + entitlement transition commit in one DB transaction.
    - Exact duplicate deliveries are ignored.
    - Unique but older state-changing events are persisted as `ignored_stale`
      and cannot overwrite newer subscription state.
    """
    if not settings.stripe_webhook_signing_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook is not configured")

    stripe.api_key = settings.stripe_api_secret
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, settings.stripe_webhook_signing_secret
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook")

    event_id = str(event["id"])
    event_type = str(event["type"])
    if event_type not in SUPPORTED_WEBHOOK_EVENTS:
        return {"result": "unsupported_ignored"}
    stripe_created = int(event.get("created") or 0)
    obj = event["data"]["object"]
    customer_id = obj.get("customer")
    subscription_id = _subscription_id(event_type, obj)

    # Fast duplicate path. The unique DB constraint remains the race-safe backstop.
    if db.scalar(
        select(SubscriptionEvent).where(SubscriptionEvent.stripe_event_id == event_id)
    ):
        return {"result": "duplicate_ignored"}

    metadata = obj.get("metadata") or {}
    user_id = metadata.get("user_id")

    # Resolve and lock user row so ordering decisions and state updates are serialized.
    user = None
    if user_id:
        user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    elif customer_id:
        user = db.scalar(
            select(User).where(User.stripe_customer_id == customer_id).with_for_update()
        )

    result = "recorded_no_user"
    desired_status = _desired_status(event_type, obj)

    if user:
        if customer_id and not user.stripe_customer_id:
            user.stripe_customer_id = customer_id
        if subscription_id:
            user.stripe_subscription_id = subscription_id

        current_created = user.last_stripe_event_created
        is_state_event = desired_status is not None
        is_stale = (
            is_state_event
            and current_created is not None
            and stripe_created < current_created
        )

        if is_stale:
            result = "ignored_stale"
        elif is_state_event:
            user.subscription_status = desired_status
            user.last_stripe_event_id = event_id
            user.last_stripe_event_type = event_type
            user.last_stripe_event_created = stripe_created
            result = "applied"
        else:
            result = "recorded_non_state"

    _maybe_inject_failure(failure_injection, "after_state_update")

    record = SubscriptionEvent(
        stripe_event_id=event_id,
        event_type=event_type,
        stripe_created=stripe_created,
        customer_id=customer_id,
        subscription_id=subscription_id,
        processing_result=result,
        payload=event,
    )
    db.add(record)
    _maybe_inject_failure(failure_injection, "after_event_add")

    try:
        _maybe_inject_failure(failure_injection, "before_commit")
        # This single commit atomically persists both the event ledger record
        # and any entitlement/state transition made above.
        db.commit()
    except IntegrityError:
        # A concurrent worker may have inserted the same event ID after the
        # fast duplicate check. Roll back the whole transaction; no partial
        # entitlement update may survive.
        db.rollback()
        existing = db.scalar(
            select(SubscriptionEvent).where(SubscriptionEvent.stripe_event_id == event_id)
        )
        if existing:
            return {"result": "duplicate_ignored"}
        raise
    except Exception:
        db.rollback()
        raise

    return {"result": result}
