"""Read-only CRM classification from account identity and stored billing facts.

Never call billing.access here: reporting must not refresh Stripe or grant access.
Derived categories apply to historical and future contacts without rewriting them.
"""

import time
from typing import Any, Literal

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Subquery

from landwolf.config import Settings
from landwolf.crm_core import Contact, Reservation
from landwolf.db import Account, BillingCustomer, BillingExemption, FeedbackEnrollment

Category = Literal["people", "all", "user", "owner", "smoke_test", "contact"]
Membership = Literal[
    "",
    "paid",
    "trial",
    "complimentary",
    "invited",
    "trial_ended",
    "billing_attention",
    "registered",
    "not_applicable",
]
CATEGORIES = {
    "user": "User",
    "owner": "Owner",
    "smoke_test": "Smoke test",
    "contact": "Contact / external project",
}
MEMBERSHIPS = {
    "paid": "Paid",
    "trial": "Trial",
    "complimentary": "Complimentary",
    "invited": "Trial invited / reserved",
    "trial_ended": "Trial ended",
    "billing_attention": "Billing needs attention",
    "registered": "Registered, no active plan",
    "not_applicable": "Not a customer account",
}
# These are the reserved-domain prefixes used by LandWolf's hosted test runners.
# Never classify by a person's name or by "test" appearing in a real email.
TEST_PREFIXES = (
    "production-smoke-",
    "staging-smoke-",
    "hunt-save-qa-",
    "hunt-browser-qa-",
    "smoke-",
    "deployment-check-",
    "national-deployment-check-",
    "free-api-check-",
    "domain-check-",
    "qa-saved-",
    "qa-navigation-",
    "qa-retirement-",
)
TEST_DOMAINS = ("example.com", "example.invalid")
TEST_EMAILS = ("support.landwolf+recovery-20261010@gmail.com",)


def segments(settings: Settings, now: int) -> Subquery:
    email = func.lower(Contact.email)
    smoke = or_(
        email.in_(TEST_EMAILS),
        *(
            email.like(prefix + "%@" + domain)
            for prefix in TEST_PREFIXES
            for domain in TEST_DOMAINS
        ),
    )
    category = case(
        (and_(Account.id.is_not(None), Account.id == settings.owner_account_id), "owner"),
        (and_(Contact.project_id == "landwolf", smoke), "smoke_test"),
        (Account.id.is_not(None), "user"),
        else_="contact",
    )
    live_grant = and_(
        BillingExemption.status == "active",
        or_(BillingExemption.expires_at.is_(None), BillingExemption.expires_at > now),
    )
    grant_trial = and_(
        live_grant,
        Reservation.kind == "trial",
        Reservation.state == "activated",
        Reservation.expires_at == BillingExemption.expires_at,
        Reservation.expires_at > now,
    )
    pilot_trial = and_(
        FeedbackEnrollment.state == "active",
        FeedbackEnrollment.accepted_at.is_not(None),
        FeedbackEnrollment.expires_at > now,
    )
    membership = case(
        (category != "user", "not_applicable"),
        (
            and_(BillingCustomer.subscription_status == "active", BillingCustomer.paid_until > now),
            "paid",
        ),
        (or_(grant_trial, pilot_trial), "trial"),
        (live_grant, "complimentary"),
        (BillingCustomer.subscription_status == "trialing", "trial"),
        (
            or_(
                and_(Reservation.kind == "trial", Reservation.state == "reserved"),
                and_(
                    FeedbackEnrollment.state == "invited", FeedbackEnrollment.accepted_at.is_(None)
                ),
                and_(
                    FeedbackEnrollment.account_id.is_(None),
                    Account.email.in_(tuple(str(e) for e in settings.pilot_invite_emails)),
                ),
            ),
            "invited",
        ),
        (
            BillingCustomer.subscription_status.in_(("past_due", "unpaid", "incomplete", "paused")),
            "billing_attention",
        ),
        (
            or_(
                and_(Reservation.kind == "trial", Reservation.state.in_(("activated", "revoked"))),
                FeedbackEnrollment.accepted_at.is_not(None),
            ),
            "trial_ended",
        ),
        else_="registered",
    )
    return (
        select(
            Contact.id.label("contact_id"),
            category.label("account_category"),
            membership.label("membership"),
            BillingCustomer.synced_at.label("billing_synced_at"),
            BillingCustomer.subscription_status.label("subscription_status"),
            BillingCustomer.paid_until.label("paid_until"),
        )
        .select_from(Contact)
        .outerjoin(
            Account,
            and_(
                Contact.project_id == "landwolf",
                Contact.external_id == Account.id,
                Contact.email == Account.email,
            ),
        )
        .outerjoin(BillingCustomer, BillingCustomer.account_id == Account.id)
        .outerjoin(
            BillingExemption,
            and_(BillingExemption.account_id == Account.id, BillingExemption.status == "active"),
        )
        .outerjoin(FeedbackEnrollment, FeedbackEnrollment.account_id == Account.id)
        .outerjoin(Reservation, Reservation.contact_id == Contact.id)
        .subquery()
    )


def summary(session: Session, rows: Subquery, now: int) -> dict[str, Any]:
    categories = dict.fromkeys(CATEGORIES, 0)
    memberships = dict.fromkeys((key for key in MEMBERSHIPS if key != "not_applicable"), 0)
    for category, membership, count in session.execute(
        select(rows.c.account_category, rows.c.membership, func.count()).group_by(
            rows.c.account_category, rows.c.membership
        )
    ):
        categories[category] += count
        if category == "user":
            memberships[membership] += count
    oldest = session.scalar(
        select(func.min(rows.c.billing_synced_at)).where(rows.c.account_category == "user")
    )
    stale = (
        session.scalar(
            select(func.count())
            .select_from(rows)
            .where(
                rows.c.account_category == "user",
                rows.c.billing_synced_at <= now - 86400,
            )
        )
        or 0
    )
    return {
        "as_of": now,
        "categories": categories,
        "memberships": memberships,
        "total_users": categories["user"],
        "oldest_billing_sync": oldest,
        "billing_records_older_than_day": stale,
        "basis": (
            "Stored account and billing records; owners and smoke tests excluded from user "
            "statistics. Paid takes precedence over trial. Trials include current owner grants, "
            "accepted pilots (including feedback overdue), and Stripe trialing status. "
            "This is not revenue or proof of a new payment."
        ),
    }


def report(session: Session, settings: Settings) -> dict[str, Any]:
    """Aggregate-only operational job: no PII, external requests or database writes."""
    now = int(time.time())
    return summary(session, segments(settings, now), now)
