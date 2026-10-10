"""Customer statistics must exclude QA identities without changing access or data."""

import csv
import io
import time
import uuid

import pytest
from sqlalchemy import func, select

from landwolf import crm_reporting
from landwolf.crm_core import Contact, Intake, Reservation, capture
from landwolf.db import Account, BillingCustomer, BillingExemption, FeedbackEnrollment


def person(session, email, *, project="landwolf", account=True):
    identity = str(uuid.uuid4())
    if account:
        session.add(Account(id=identity, email=email, password_hash="synthetic", created_at=1))
        session.flush()
    row = capture(
        session,
        project,
        Intake(
            external_id=identity, email=email, full_name="Smoke Test Realty", primary_use="research"
        ),
        source="registration",
    )
    return identity, row


def paid(session, account, now, status="active", until=None):
    session.add(
        BillingCustomer(
            account_id=account,
            customer_id="cus_" + account,
            paid_until=now + 1000 if until is None else until,
            subscription_status=status,
            synced_at=now,
        )
    )


def grant(session, account, contact, owner, now, *, kind="trial", state="active", expires=None):
    end = now + 1000 if expires is None else expires
    session.add(
        BillingExemption(
            id=str(uuid.uuid4()),
            account_id=account,
            status=state,
            granted_by_account_id=owner,
            granted_at=now - 2000,
            expires_at=end,
            created_at=now - 2000,
            updated_at=now,
        )
    )
    session.add(
        Reservation(
            contact_id=contact.id,
            kind=kind,
            days=1,
            state="activated",
            owner_id=owner,
            reason="Synthetic trial",
            created_at=now - 2000,
            activated_at=now - 2000,
            expires_at=end,
        )
    )


@pytest.mark.parametrize(
    "email,expected",
    [
        ("production-smoke-abc@example.com", "smoke_test"),
        ("staging-smoke-abc@example.com", "smoke_test"),
        ("hunt-save-qa-abc@example.com", "smoke_test"),
        ("hunt-browser-qa-abc@example.com", "smoke_test"),
        ("smoke-abc@example.com", "smoke_test"),
        ("support.landwolf+recovery-20261010@gmail.com", "smoke_test"),
        ("production-smoke-abc@gmail.com", "user"),
        ("not-production-smoke-abc@example.com", "user"),
        ("customer-test@example.com", "user"),
        ("support.landwolf@gmail.com", "user"),
    ],
)
def test_classification_is_narrow_and_automatic(client, owner_signed_in, email, expected):
    with client.app.state.factory() as session, session.begin():
        _, row = person(session, email)
        contact_id = row.id
    all_rows = client.get("/api/admin/crm/contacts?account_category=all").json()
    record = next(c for c in all_rows["contacts"] if c["id"] == contact_id)
    assert record["account_category"] == expected
    default = client.get("/api/admin/crm/contacts").json()
    assert (contact_id in {r["id"] for r in default["contacts"]}) == (expected != "smoke_test")
    assert default["statistics"]["total_users"] == (1 if expected == "user" else 0)


def test_trial_paid_overlap_expiry_and_invitation_counts(client, owner_signed_in):
    now = int(time.time())
    owner = client.app.state.settings.owner_account_id
    with client.app.state.factory() as session, session.begin():
        for label in (
            "paid",
            "trial",
            "comp",
            "expired",
            "revoked",
            "pilot",
            "invited",
            "attention",
            "new",
            "stripe_trial",
            "unpaid_active",
        ):
            account, contact = person(session, label + "@example.com")
            if label in {"trial", "paid", "comp", "expired", "revoked"}:
                grant(
                    session,
                    account,
                    contact,
                    owner,
                    now,
                    kind="complimentary" if label == "comp" else "trial",
                    state="revoked" if label == "revoked" else "active",
                    expires=now if label == "expired" else None,
                )
            if label in {"paid", "attention", "stripe_trial", "unpaid_active"}:
                paid(
                    session,
                    account,
                    now,
                    status={"attention": "past_due", "stripe_trial": "trialing"}.get(
                        label, "active"
                    ),
                    until=0 if label == "unpaid_active" else None,
                )
            if label in {"pilot", "invited"}:
                session.add(
                    FeedbackEnrollment(
                        account_id=account,
                        invited_by_account_id=owner,
                        invited_at=now - 500,
                        state="active" if label == "pilot" else "invited",
                        accepted_at=now - 400 if label == "pilot" else None,
                        expires_at=now + 1000 if label == "pilot" else None,
                        terms_version="fixture",
                    )
                )
        qa, _ = person(session, "production-smoke-paid@example.com")
        paid(session, qa, now)
    data = client.get("/api/admin/crm/contacts?account_category=user&membership=trial").json()
    assert data["total"] == 3
    assert {r["email"] for r in data["contacts"]} == {
        "trial@example.com",
        "pilot@example.com",
        "stripe_trial@example.com",
    }
    stats = data["statistics"]
    assert stats["total_users"] == 11
    assert stats["categories"] == {"user": 11, "owner": 1, "smoke_test": 1, "contact": 0}
    assert stats["memberships"] == {
        "paid": 1,
        "trial": 3,
        "complimentary": 1,
        "invited": 1,
        "trial_ended": 2,
        "billing_attention": 1,
        "registered": 2,
    }
    assert sum(stats["memberships"].values()) == stats["total_users"]
    # Classification is strictly read-only; no expired/revoked grant is reactivated.
    with client.app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(BillingExemption)) == 5


def test_owner_precedence_and_external_identity_isolation(client, owner_signed_in):
    from landwolf.crm_core import Project

    owner = client.app.state.settings.owner_account_id
    with client.app.state.factory() as session, session.begin():
        session.get(Account, owner).email = "production-smoke-owner@example.com"
        session.scalar(
            select(Contact).where(Contact.external_id == owner)
        ).email = "production-smoke-owner@example.com"
        session.add(Project(id="external", name="External", created_at=1))
        session.flush()
        _, external = person(
            session, "production-smoke-ext@example.com", project="external", account=False
        )
        external.external_id = owner
    data = client.get("/api/admin/crm/contacts").json()
    assert data["total"] == 2
    assert data["statistics"]["categories"] == {
        "owner": 1,
        "user": 0,
        "smoke_test": 0,
        "contact": 1,
    }


def test_filter_before_pagination_csv_and_statistics_scope(client, owner_signed_in):
    with client.app.state.factory() as session, session.begin():
        for i in range(55):
            person(session, f"production-smoke-{i}@example.com")
            person(session, f"customer-{i}@example.com")
    first = client.get("/api/admin/crm/contacts?account_category=user").json()
    second = client.get("/api/admin/crm/contacts?account_category=user&page=2").json()
    assert first["total"] == 55 and len(first["contacts"]) == 50
    assert len(second["contacts"]) == 5
    assert not {c["id"] for c in first["contacts"]} & {c["id"] for c in second["contacts"]}
    for suffix, expected in (
        ("", 56),
        ("?account_category=smoke_test", 55),
        ("?account_category=user", 55),
    ):
        response = client.get("/api/admin/crm/contacts.csv" + suffix)
        assert response.status_code == 200
        records = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
        assert len(records) == expected
        assert (
            all(c["account_category"] == "smoke_test" for c in records)
            if "smoke_test" in suffix
            else all(c["account_category"] != "smoke_test" for c in records)
        )
    data = client.get("/api/admin/crm/contacts?q=customer-54&account_category=user").json()
    assert data["total"] == data["statistics"]["total_users"] == 1
    assert client.get("/api/admin/crm/contacts?account_category=invalid").status_code == 422
    assert client.get("/api/admin/crm/contacts.csv?membership=invalid").status_code == 422


def test_statistics_privacy_and_no_network_or_writes(client, signed_in, monkeypatch):
    assert client.get("/api/admin/crm/statistics").status_code == 403
    with client.app.state.factory() as session:
        client.app.state.settings.owner_account_id = session.scalar(select(Account.id))

    def forbidden(*args, **kwargs):
        raise AssertionError("Reporting must not change billing or access")

    monkeypatch.setattr("landwolf.billing.refresh_customer", forbidden)
    monkeypatch.setattr("landwolf.crm_access.activate_reserved", forbidden)
    response = client.get("/api/admin/crm/statistics")
    assert response.status_code == 200 and response.json()["total_users"] == 0
    assert "@" not in response.text and "customer_id" not in response.text
    client.cookies.clear()
    assert client.get("/api/admin/crm/statistics").status_code == 401


def test_expired_allowlisted_pilot_and_replaced_trial_not_misreported(client, owner_signed_in):
    now = int(time.time())
    owner = client.app.state.settings.owner_account_id
    client.app.state.settings.pilot_invite_emails = ("expired-pilot@example.com",)
    with client.app.state.factory() as session, session.begin():
        account, _ = person(session, "expired-pilot@example.com")
        session.add(
            FeedbackEnrollment(
                account_id=account,
                invited_by_account_id=owner,
                invited_at=now - 2000,
                state="active",
                accepted_at=now - 1000,
                expires_at=now,
                terms_version="fixture",
            )
        )
        account, contact = person(session, "replaced@example.com")
        grant(session, account, contact, owner, now)
        session.flush()
        session.get(Reservation, contact.id).expires_at = now - 1
        customer = BillingCustomer(
            account_id=account,
            customer_id="cus_stale",
            paid_until=0,
            subscription_status="none",
            synced_at=now - 86401,
        )
        session.add(customer)
    result = client.get("/api/admin/crm/statistics").json()
    assert result["memberships"]["trial_ended"] == 1
    assert result["memberships"]["complimentary"] == 1
    assert result["memberships"]["invited"] == result["memberships"]["trial"] == 0
    assert result["billing_records_older_than_day"] == 1
    with client.app.state.factory() as session:
        assert crm_reporting.report(session, client.app.state.settings)["total_users"] == 2
