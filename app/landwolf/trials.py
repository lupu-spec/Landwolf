"""Explicit self-service feedback trial; never convert legacy pilots or CRM grants.

Only the bounded worker may create a paid subscription. No client clock, return
URL or webhook payload can authorize a charge. Stripe owns payment details.
"""

import asyncio
import logging
import smtplib
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import httpx
from fastapi import HTTPException
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from landwolf import billing, feedback, recovery
from landwolf.config import Settings
from landwolf.crm_core import Contact, Reservation
from landwolf.db import (
    Account,
    AccountRestriction,
    BillingCustomer,
    BillingExemption,
    FeedbackEnrollment,
    FeedbackTrial,
    TrialMessage,
    TrialResponse,
)

LOGGER = logging.getLogger(__name__)
DAY = 86400
DAYS = (30, 60, 90)
TERMS_VERSION = "feedback-trial-v1-2026-10-10"
TERMS = (
    "I authorize L91 LLC (LandWolf) to save my payment method with Stripe. "
    "There is no charge to start. My trial provides up to 90 days of access, with feedback "
    "due on days 30, 60 and 90. If I miss feedback, LandWolf will email a notice giving "
    "me at least seven days to complete it or cancel. If I do neither, I authorize "
    "LandWolf to begin a $29 USD monthly subscription on the date in that notice, "
    "renewing monthly until I cancel. There is no back-billing or feedback penalty. "
    "Completing all three feedback requests ends this trial without an automatic charge. "
    "I can cancel the trial in Membership before conversion, ending trial access; "
    "after conversion "
    "I can cancel renewal in Manage billing. CRM-granted access follows its own terms."
)
OPEN_STATES = ("setup", "active", "notice", "converting", "blocked")


class AcceptInput(feedback.StrictContract):
    terms_version: Literal["feedback-trial-v1-2026-10-10"]
    accepted_recurring_terms: bool = Field(strict=True)


class ResponseInput(feedback.StrictContract):
    day: Literal[30, 60, 90]
    answers: feedback.Answers


def enabled(settings: Settings) -> bool:
    return bool(
        settings.payments_enabled
        and settings.feedback_trial_launch_at
        and recovery.Mailer(settings).enabled
    )


def exempt(session: Session, account: Account, settings: Settings) -> bool:
    """Any direct grant/pilot history prevents later automatic trial conversion."""
    return bool(
        account.id == settings.owner_account_id
        or account.email.casefold() in settings.pilot_invite_emails
        or session.get(FeedbackEnrollment, account.id)
        or session.scalar(
            select(BillingExemption.id).where(BillingExemption.account_id == account.id).limit(1)
        )
        or session.scalar(
            select(Reservation.contact_id)
            .join(Contact, Contact.id == Reservation.contact_id)
            .where(Contact.project_id == "landwolf", Contact.external_id == account.id)
            .limit(1)
        )
    )


def eligible(session: Session, account: Account, settings: Settings) -> bool:
    return bool(
        enabled(settings)
        and account.created_at >= settings.feedback_trial_launch_at
        and not exempt(session, account, settings)
        and session.get(FeedbackTrial, account.id) is None
        and session.get(BillingCustomer, account.id) is None
    )


def responses(session: Session, account_id: str) -> set[int]:
    return set(
        session.scalars(select(TrialResponse.day).where(TrialResponse.account_id == account_id))
    )


def status(session: Session, account: Account, settings: Settings) -> dict[str, Any]:
    row = session.get(FeedbackTrial, account.id)
    current = int(time.time())
    complete = responses(session, account.id) if row else set()
    result: dict[str, Any] = {
        "eligible": eligible(session, account, settings),
        "email_verified": recovery.verified(session, account.id),
        "terms_version": TERMS_VERSION,
        "terms": TERMS,
        "state": row.state if row else "none",
        "access_allowed": False,
        "started_at": row.started_at if row else None,
        "expires_at": row.expires_at if row else None,
        "charge_at": row.charge_at if row and row.state == "notice" else None,
        "completed_days": sorted(complete),
        "surveys": [],
    }
    if row and row.started_at:
        result["access_allowed"] = row.state in {"active", "notice"} and current < (
            row.expires_at or 0
        )
        result["surveys"] = [
            {
                "day": day,
                "due_at": row.started_at + day * DAY,
                "opens_at": row.started_at + (day - 7) * DAY,
                "complete": day in complete,
            }
            for day in DAYS
        ]
    return result


def locked(session: Session, account_id: str) -> FeedbackTrial:
    billing.lock_account(session, account_id)
    row = session.get(FeedbackTrial, account_id, populate_existing=True)
    if row is None:
        raise HTTPException(404, "No feedback trial exists")
    return row


def setup_fields(
    row: FeedbackTrial, customer: BillingCustomer, settings: Settings
) -> dict[str, str]:
    suffix = "".join(chr(97 + int(c, 16)) for c in row.attempt_id.replace("-", "")[:8])
    return {
        "mode": "setup",
        "currency": "usd",
        "managed_payments[enabled]": "false",
        "customer": customer.customer_id,
        "client_reference_id": row.account_id,
        "integration_identifier": "landwolf-feedback-trial-" + suffix,
        "metadata[app]": "landwolf",
        "metadata[trial_attempt]": row.attempt_id,
        "metadata[terms_version]": TERMS_VERSION,
        "setup_intent_data[metadata][trial_attempt]": row.attempt_id,
        "setup_intent_data[description]": "LandWolf trial: conditional $29/month consent",
        "custom_text[submit][message]": TERMS,
        "success_url": settings.public_origin + "/?billing=return",
        "cancel_url": settings.public_origin + "/?billing=cancelled",
        "expires_at": str(row.consent_at + billing.CHECKOUT_SECONDS),
    }


def checkout(
    session: Session, account: Account, settings: Settings, body: AcceptInput
) -> dict[str, str]:
    if body.accepted_recurring_terms is not True:
        raise HTTPException(422, "Please explicitly agree to the trial billing terms")
    billing.lock_account(session, account.id)
    row = session.get(FeedbackTrial, account.id)
    if row is None and not eligible(session, account, settings):
        raise HTTPException(409, "This offer is for eligible new self-service accounts")
    if not enabled(settings) or exempt(session, account, settings):
        raise HTTPException(409, "This account does not need this billing trial")
    if not recovery.verified(session, account.id):
        raise HTTPException(409, "Verify your email first so trial notices reach you")
    if row and (
        row.state != "setup" or row.consent_at + billing.CHECKOUT_SECONDS <= int(time.time())
    ):
        raise HTTPException(
            409, "This trial setup has ended; contact support or choose a membership"
        )
    if row is None:
        current = int(time.time())
        row = FeedbackTrial(
            account_id=account.id,
            state="setup",
            terms_version=TERMS_VERSION,
            consent_text=TERMS,
            consent_at=current,
            attempt_id=str(uuid.uuid4()),
            updated_at=current,
        )
        session.add(row)
        session.commit()
    customer = billing.customer_for_checkout(session, account, settings)
    row = locked(session, account.id)
    api = billing.StripeAPI(settings)
    existing = billing.subscriptions(api, customer)
    if any(s.get("status") not in {"canceled", "incomplete_expired"} for s in existing):
        raise HTTPException(409, "An existing membership needs attention. Open Manage billing")
    result = (
        api.call("GET", "/checkout/sessions/" + billing.identifier(row.checkout_id, "cs_live_"))
        if row.checkout_id
        else api.call(
            "POST",
            "/checkout/sessions",
            setup_fields(row, customer, settings),
            idempotency_key="landwolf-trial-setup-" + row.attempt_id,
        )
    )
    if (
        result.get("livemode") is not True
        or result.get("mode") != "setup"
        or result.get("customer") != customer.customer_id
        or result.get("client_reference_id") != account.id
    ):
        raise billing.unavailable()
    row.checkout_id = billing.identifier(result.get("id"), "cs_live_")
    session.commit()
    if result.get("status") != "open":
        raise HTTPException(409, "Setup is processing; use Check payment status")
    return {"url": billing.trusted_url(result.get("url"), "checkout.stripe.com")}


def reconcile_setup(session: Session, account: Account, settings: Settings) -> None:
    row = session.get(FeedbackTrial, account.id)
    customer = session.get(BillingCustomer, account.id)
    if not row or row.state != "setup" or not customer:
        return
    row = locked(session, account.id)
    if not row.checkout_id:
        # Lost creation responses are replayed only while Stripe retains idempotency.
        if row.consent_at + billing.CHECKOUT_SECONDS <= int(time.time()):
            row.state = "blocked"
            return
        result = billing.StripeAPI(settings).call(
            "POST",
            "/checkout/sessions",
            setup_fields(row, customer, settings),
            idempotency_key="landwolf-trial-setup-" + row.attempt_id,
        )
        row.checkout_id = billing.identifier(result.get("id"), "cs_live_")
    else:
        result = billing.StripeAPI(settings).call(
            "GET", "/checkout/sessions/" + billing.identifier(row.checkout_id, "cs_live_")
        )
    if (
        result.get("livemode") is not True
        or result.get("mode") != "setup"
        or result.get("customer") != customer.customer_id
        or result.get("client_reference_id") != account.id
    ):
        raise billing.unavailable()
    if result.get("status") == "expired":
        row.state = "cancelled"
        return
    if result.get("status") != "complete":
        return
    intent = billing.StripeAPI(settings).call(
        "GET", "/setup_intents/" + billing.identifier(result.get("setup_intent"), "seti_")
    )
    if (
        intent.get("status") != "succeeded"
        or intent.get("livemode") is not True
        or intent.get("customer") != customer.customer_id
    ):
        raise billing.unavailable()
    if exempt(session, account, settings):
        row.state = "cancelled"
        return
    row.payment_method_id = billing.identifier(intent.get("payment_method"), "pm_")
    row.started_at = int(time.time())
    row.expires_at = row.started_at + 90 * DAY
    row.state = "active"
    row.updated_at = row.started_at


def submit(
    session: Session, account: Account, settings: Settings, body: ResponseInput
) -> dict[str, Any]:
    row = locked(session, account.id)
    current = int(time.time())
    if not row.started_at or row.state not in {"active", "notice"}:
        raise HTTPException(409, "Feedback is available for an active trial")
    if current < row.started_at + (body.day - 7) * DAY:
        raise HTTPException(409, "This feedback request opens seven days before its due date")
    if session.get(TrialResponse, (account.id, body.day)) is None:
        session.add(
            TrialResponse(
                account_id=account.id,
                day=body.day,
                answers=body.answers.model_dump(),
                submitted_at=current,
            )
        )
        session.flush()
    if row.notice_day == body.day:
        row.notice_day = None
        row.charge_at = None
        row.state = "active"
    if responses(session, account.id) == set(DAYS) and current >= (row.expires_at or 0):
        row.state = "completed"
    row.updated_at = current
    session.commit()
    return status(session, account, settings)


def cancel(session: Session, account: Account, settings: Settings) -> dict[str, Any]:
    row = locked(session, account.id)
    if row.state == "subscribed":
        raise HTTPException(409, "Your trial already converted; cancel renewal in Manage billing")
    row.state = "cancelled"
    row.next_check_at = 0
    row.cancelled_at = int(time.time())
    row.charge_at = None
    row.updated_at = row.cancelled_at
    session.commit()
    try:
        row = locked(session, account.id)
        stop_renewal(session, row, settings)
        session.commit()
    except (HTTPException, httpx.HTTPError):
        session.rollback()
        LOGGER.warning("Trial cancellation recorded; Stripe reconciliation pending")
    return status(session, account, settings)


def date(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, UTC).strftime("%B %d, %Y at %H:%M UTC")


def send_message(
    session: Session,
    row: FeedbackTrial,
    account: Account,
    settings: Settings,
    key: str,
    subject: str,
    body: str,
    current: int,
) -> bool:
    message = session.get(TrialMessage, (row.account_id, key))
    if message and message.sent_at:
        return True
    if message and (message.attempts >= 5 or message.next_attempt_at > current):
        return False
    if message is None:
        message = TrialMessage(
            account_id=row.account_id,
            key=key,
            subject=subject,
            body=body,
            created_at=current,
            attempts=0,
        )
        session.add(message)
    # A retry may give a later deadline; retain the final text actually accepted.
    message.body = body
    message.attempts += 1
    message.next_attempt_at = current + 3600
    try:
        asyncio.run(
            recovery.Mailer(settings).send_text(
                account.email,
                subject,
                body,
                row.attempt_id + "-" + key + "-" + str(message.attempts),
            )
        )
    except (httpx.HTTPError, smtplib.SMTPException, OSError, RuntimeError):
        LOGGER.warning("Feedback trial notice delivery failed; automatic conversion withheld")
        return False
    message.sent_at = current
    return True


def conversion(
    session: Session,
    row: FeedbackTrial,
    customer: BillingCustomer,
    settings: Settings,
    current: int,
) -> None:
    api = billing.StripeAPI(settings)
    existing = billing.subscriptions(api, customer)
    matching = [
        s for s in existing if (s.get("metadata") or {}).get("feedback_trial") == row.attempt_id
    ]
    if matching:
        finish_conversion(session, row, customer, settings, matching[0], current)
        return
    if any(s.get("status") not in {"canceled", "incomplete_expired"} for s in existing):
        row.state = "blocked"
        return
    if row.conversion_attempt_at and current - row.conversion_attempt_at >= 20 * 3600:
        row.state = "blocked"  # Never retry beyond Stripe's idempotency retention.
        return
    if not row.conversion_attempt_at:
        row.conversion_attempt_at = current
        row.state = "converting"
        session.commit()
        row = locked(session, row.account_id)
        account = session.get(Account, row.account_id)
        if row.state != "converting" or account is None or exempt(session, account, settings):
            row.state = "cancelled"
            return
        if row.notice_day in responses(session, row.account_id):
            row.state = "active"
            row.charge_at = None
            return
    result = api.call(
        "POST",
        "/subscriptions",
        {
            "customer": customer.customer_id,
            "items[0][price]": billing.price_id(settings, "monthly"),
            "items[0][quantity]": "1",
            "default_payment_method": billing.identifier(row.payment_method_id, "pm_"),
            "collection_method": "charge_automatically",
            "payment_behavior": "default_incomplete",
            "off_session": "true",
            "billing_mode[type]": "flexible",
            "proration_behavior": "none",
            "metadata[app]": "landwolf",
            "metadata[feedback_trial]": row.attempt_id,
            "metadata[account_id]": row.account_id,
            "metadata[terms_version]": row.terms_version,
            "description": "LandWolf $29/month after feedback notice; no back-billing",
        },
        idempotency_key="landwolf-trial-convert-" + row.attempt_id,
    )
    if result.get("livemode") is not True or result.get("customer") != customer.customer_id:
        raise billing.unavailable()
    finish_conversion(session, row, customer, settings, result, current)


def finish_conversion(
    session: Session,
    row: FeedbackTrial,
    customer: BillingCustomer,
    settings: Settings,
    subscription: dict[str, Any],
    current: int,
) -> None:
    """Create without payment, verify the first invoice, then explicitly pay once."""
    api = billing.StripeAPI(settings)
    row.subscription_id = billing.identifier(subscription.get("id"), "sub_")
    if subscription.get("status") == "incomplete":
        if not row.conversion_attempt_at or current - row.conversion_attempt_at >= 20 * 3600:
            row.state = "blocked"
            return
        invoice_id = billing.identifier(subscription.get("latest_invoice"), "in_")
        invoice = api.call("GET", "/invoices/" + invoice_id)
        lines = invoice.get("lines") or {}
        data = lines.get("data") or []
        if (
            invoice.get("livemode") is not True
            or invoice.get("customer") != customer.customer_id
            or invoice.get("currency") != "usd"
            or invoice.get("total") != 2900
            or invoice.get("amount_due") != 2900
            or lines.get("has_more") is not False
            or len(data) != 1
            or (data[0].get("pricing") or {}).get("price_details", {}).get("price")
            != billing.price_id(settings, "monthly")
            or (invoice.get("parent") or {}).get("subscription_details", {}).get("subscription")
            != row.subscription_id
        ):
            row.state = "blocked"
            return
        if invoice.get("status") == "open":
            prepared = api.call(
                "POST",
                "/invoices/" + invoice_id,
                {"statement_descriptor": "LANDWOLF* TRIAL OVER", "auto_advance": "false"},
                idempotency_key="landwolf-trial-descriptor-" + row.attempt_id,
            )
            if prepared.get("statement_descriptor") != "LANDWOLF* TRIAL OVER":
                raise billing.unavailable()
            api.call(
                "POST",
                "/invoices/" + invoice_id + "/pay",
                {
                    "payment_method": billing.identifier(row.payment_method_id, "pm_"),
                    "off_session": "true",
                },
                idempotency_key="landwolf-trial-pay-" + row.attempt_id,
            )
        elif invoice.get("status") != "paid":
            row.state = "blocked"
            return
    row.state = "subscribed"
    billing.store_subscriptions(customer, billing.subscriptions(api, customer), settings)


def stop_renewal(session: Session, row: FeedbackTrial, settings: Settings) -> None:
    customer = session.get(BillingCustomer, row.account_id)
    if not row.conversion_attempt_at or not customer:
        return
    api = billing.StripeAPI(settings)
    for item in billing.subscriptions(api, customer):
        if (item.get("metadata") or {}).get("feedback_trial") != row.attempt_id:
            continue
        row.subscription_id = billing.identifier(item.get("id"), "sub_")
        if item.get("status") == "incomplete":
            api.call(
                "DELETE",
                "/subscriptions/" + row.subscription_id,
                idempotency_key="landwolf-trial-void-" + row.attempt_id,
            )
        elif item.get("status") not in {"canceled", "incomplete_expired"} and not item.get(
            "cancel_at_period_end"
        ):
            api.call(
                "POST",
                "/subscriptions/" + row.subscription_id,
                {"cancel_at_period_end": "true"},
                idempotency_key="landwolf-trial-cancel-" + row.attempt_id,
            )


def process_one(session: Session, account: Account, settings: Settings, current: int) -> None:
    row = locked(session, account.id)
    link = settings.public_origin + "/?billing=return"
    footer = f"\n\nManage billing or cancel: {link}\nSupport: support.landwolf@gmail.com\nL91 LLC"
    if row.state == "cancelled":
        # A lost Stripe response may conceal a subscription created before cancellation.
        # Reconcile only this trial; never retry its create request after cancellation.
        stop_renewal(session, row, settings)
        send_message(
            session,
            row,
            account,
            settings,
            "cancelled",
            "Your LandWolf feedback trial cancellation",
            "Your trial is cancelled and no new conversion will be initiated. "
            "If conversion was already processing, its result is in Manage billing and "
            "renewal will be cancelled. Contact support if you believe a charge is incorrect."
            + footer,
            current,
        )
        return
    if row.state == "subscribed":
        anniversary = (current - (row.conversion_attempt_at or current)) // (365 * DAY)
        message_key = f"annual-{anniversary}" if anniversary else "conversion"
        sent = session.get(TrialMessage, (account.id, message_key))
        if sent and sent.sent_at:
            row.next_check_at = (row.conversion_attempt_at or current) + (
                anniversary + 1
            ) * 365 * DAY
            return
        customer = session.get(BillingCustomer, account.id)
        if customer:
            billing.store_subscriptions(
                customer, billing.subscriptions(billing.StripeAPI(settings), customer), settings
            )
            text = (
                "Your feedback trial converted to a $29 USD monthly membership "
                "under your accepted terms and prior notice. No past trial days are billed. "
                "It renews monthly until cancelled. View invoices, payment status and "
                "cancel renewal online in Manage billing."
            )
            send_message(
                session,
                row,
                account,
                settings,
                "conversion",
                "Your LandWolf membership and billing details",
                text + footer,
                current,
            )
            year = (current - (row.conversion_attempt_at or current)) // (365 * DAY)
            if (
                year >= 1
                and customer.subscription_status == "active"
                and not customer.cancel_at_period_end
            ):
                send_message(
                    session,
                    row,
                    account,
                    settings,
                    f"annual-{year}",
                    "Annual reminder: your LandWolf membership",
                    "Your LandWolf membership renews at $29 USD monthly until you cancel. "
                    "Cancel renewal in Manage billing; access continues through the paid period."
                    + footer,
                    current,
                )
        return
    if row.state not in OPEN_STATES:
        return
    restriction = session.get(AccountRestriction, account.id)
    if exempt(session, account, settings) or (restriction is not None and restriction.suspended):
        row.state = "cancelled"
        row.cancelled_at = current
        row.charge_at = None
        return
    if row.state == "setup":
        reconcile_setup(session, account, settings)
        return
    if row.state == "blocked" or not row.started_at:
        return
    if current > row.started_at + 105 * DAY:
        row.state = "blocked"
        return
    link = settings.public_origin + "/?billing=return"
    footer = (
        f"\n\nManage your trial or cancel online: {link}\n"
        "Support: support.landwolf@gmail.com\nL91 LLC — LandWolf\n"
    )
    welcome = (
        TERMS
        + "\n\nYour trial started "
        + date(row.started_at)
        + ". Access ends "
        + date(row.expires_at or 0)
        + ".\n"
        + "\n".join(f"Day {day} feedback due: {date(row.started_at + day * DAY)}" for day in DAYS)
        + footer
    )
    if not send_message(
        session,
        row,
        account,
        settings,
        "welcome",
        "Your LandWolf feedback trial — dates and billing terms",
        welcome,
        current,
    ):
        return
    done = responses(session, account.id)
    if done == set(DAYS):
        if current >= (row.expires_at or 0):
            row.state = "completed"
            send_message(
                session,
                row,
                account,
                settings,
                "complete",
                "Thank you — your LandWolf trial finished with no charge",
                "Thanks for helping improve LandWolf. You completed every feedback request. "
                "No subscription was started and no automatic trial charge will follow. "
                "You can choose a membership whenever you are ready." + footer,
                current,
            )
        return
    for day in DAYS:
        if day in done:
            continue
        due = row.started_at + day * DAY
        if current < due - 7 * DAY:
            return
        if current < due:
            send_message(
                session,
                row,
                account,
                settings,
                f"reminder-{day}",
                "A quick LandWolf feedback check-in is ready",
                f"Your day {day} feedback is due {date(due)}. "
                "Honest feedback, including that you have not used the app, is welcome. "
                "Complete the short form in Membership. There is no charge for this reminder. "
                "Missing feedback may start $29/month billing "
                "only after a separate seven-day notice." + footer,
                current,
            )
            return
        if row.state == "converting":
            customer = session.get(BillingCustomer, account.id)
            if customer:
                conversion(session, row, customer, settings, current)
            return
        if row.state != "notice":
            charge_at = current + 7 * DAY + 3600
            body = (
                f"We have not received your day {day} feedback. "
                f"Please complete it or cancel before {date(charge_at)} to avoid a charge. "
                "Otherwise, under your accepted trial terms, a $29 USD monthly membership "
                "will begin on that date and renew monthly until cancelled. "
                "No past trial days will be billed. Feedback of any sentiment is accepted; "
                "not using the app is a valid response." + footer
            )
            if send_message(
                session,
                row,
                account,
                settings,
                f"notice-{day}",
                "LandWolf: feedback or cancellation needed before $29/month billing",
                body,
                current,
            ):
                row.notice_day = day
                row.charge_at = charge_at
                row.state = "notice"
            return
        if row.charge_at is None or current < row.charge_at:
            return
        # Do not charge at an unexpected later time after an outage.
        if current > row.charge_at + DAY:
            row.state = "blocked"
            return
        notice = session.get(TrialMessage, (account.id, f"notice-{day}"))
        if not notice or not notice.sent_at or current < notice.sent_at + 7 * DAY:
            row.state = "blocked"
            return
        customer = session.get(BillingCustomer, account.id)
        if customer:
            conversion(session, row, customer, settings, current)
        return


def tick(factory: sessionmaker[Session], settings: Settings) -> None:
    if not enabled(settings):
        return
    with factory() as session:
        ids = list(
            session.scalars(
                select(FeedbackTrial.account_id)
                .where(
                    FeedbackTrial.state.in_((*OPEN_STATES, "cancelled", "subscribed")),
                    FeedbackTrial.next_check_at <= int(time.time()),
                )
                .order_by(FeedbackTrial.updated_at, FeedbackTrial.account_id)
                .limit(100)
            )
        )
    for account_id in ids:
        with factory() as session:
            try:
                account = session.get(Account, account_id)
                if account:
                    current = int(time.time())
                    process_one(session, account, settings, current)
                    row = session.get(FeedbackTrial, account_id)
                    if row:
                        row.updated_at = current
                    session.commit()
            except (HTTPException, httpx.HTTPError):
                session.rollback()
                LOGGER.warning(
                    "Feedback trial reconciliation delayed; no new unverified billing attempt"
                )


async def run(factory: sessionmaker[Session], settings: Settings) -> None:
    while True:
        try:
            await run_in_threadpool(tick, factory, settings)
        except Exception:
            LOGGER.exception("Feedback trial worker paused until next bounded retry")
        await asyncio.sleep(3600)
