"""Owner identity, manual-contact registration, and account administration regressions."""

import time

import pytest
from conftest import register
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from landwolf import billing, crm_core
from landwolf.db import (
    Account,
    AccountAction,
    AccountAdminAudit,
    AccountEmail,
    BillingExemption,
    SchemaVersion,
    initialize,
)

HEADERS = {"Origin": "http://testserver", "X-LandWolf-Client": "web"}
PROFILE = {"full_name": "Fixture Contact", "primary_use": "exploring"}
EMAIL = "managed-fixture@example.com"


def create(client, headers, email=EMAIL, **values):
    response = client.post(
        "/api/admin/crm/contacts", headers=headers, json={**PROFILE, "email": email, **values}
    )
    assert response.status_code == 201, response.text
    return response.json()


def row(client, id):
    return client.get("/api/admin/crm/contacts/" + id).json()["contact"]


def change(client, headers, contact, route, **values):
    return client.post(
        f"/api/admin/crm/contacts/{contact['id']}/{route}",
        headers=headers,
        json={
            "revision": row(client, contact["id"])["revision"],
            "reason": "Owner fixture request",
            **values,
        },
    )


def details(client, contact):
    return client.get(f"/api/admin/crm/contacts/{contact['id']}/account").json()


def test_manual_registration_preserves_record_and_notes(client, owner_signed_in):
    c = create(client, owner_signed_in)
    assert not details(client, c)["registered"]
    with TestClient(client.app) as customer:
        register(customer, EMAIL)
        assert customer.get(f"/api/admin/crm/contacts/{c['id']}/account").status_code == 403
    assert client.get("/api/admin/crm/contacts?q=" + EMAIL).json()["total"] == 1
    saved = row(client, c["id"])
    assert saved["id"] == c["id"] and saved["source"] == "owner_manual"
    assert not saved["external_id"].startswith("manual:")
    assert details(client, c)["registered"]
    with client.app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(crm_core.Contact)) == 2
        assert db.scalar(select(AccountAdminAudit).where(AccountAdminAudit.contact_id == c["id"]))


def test_trial_reservation_requires_verified_mailbox_and_activates_once(client, owner_signed_in):
    c = create(client, owner_signed_in)
    result = change(client, owner_signed_in, c, "access", action="trial", days=90)
    assert result.status_code == 200 and result.json()["state"] == "reserved"
    with TestClient(client.app) as customer:
        register(customer, EMAIL)
        client.app.state.settings.payments_enabled = True
        status = customer.get("/api/billing/status").json()
        assert not status["allowed"]
        assert details(client, c)["reservation"]["state"] == "reserved"
        with client.app.state.factory() as db, db.begin():
            account = db.scalar(select(Account).where(Account.email == EMAIL))
            db.add(AccountEmail(account_id=account.id, verified_at=int(time.time())))
        first = customer.get("/api/billing/status").json()
        assert first["allowed"] and first["reason"] == "complimentary"
        second = customer.get("/api/billing/status").json()
        assert second["allowed"]
    d = details(client, c)
    assert d["reservation"]["state"] == "activated"
    assert abs(d["expires_at"] - int(time.time()) - 90 * 86400) < 30
    with client.app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(BillingExemption)) == 1


def test_owner_can_activate_extend_and_revoke_registered_trial(client, owner_signed_in):
    c = create(client, owner_signed_in)
    with TestClient(client.app) as customer:
        register(customer, EMAIL)
        client.app.state.settings.payments_enabled = True
        assert (
            change(client, owner_signed_in, c, "access", action="trial", days=7).status_code == 200
        )
        assert customer.get("/api/billing/status").json()["allowed"]
        old = details(client, c)["expires_at"]
        assert (
            change(client, owner_signed_in, c, "access", action="trial", days=30).status_code == 200
        )
        assert details(client, c)["expires_at"] > old
        assert change(client, owner_signed_in, c, "access", action="revoke").status_code == 200
        assert not customer.get("/api/billing/status").json()["allowed"]


def test_revoked_reservation_never_grants_access(client, owner_signed_in):
    c = create(client, owner_signed_in)
    change(client, owner_signed_in, c, "access", action="trial", days=10)
    change(client, owner_signed_in, c, "access", action="revoke")
    with TestClient(client.app) as customer:
        register(customer, EMAIL)
        with client.app.state.factory() as db, db.begin():
            account = db.scalar(select(Account).where(Account.email == EMAIL))
            db.add(AccountEmail(account_id=account.id, verified_at=int(time.time())))
        customer.get("/api/billing/status")
    assert not details(client, c)["complimentary"]


def test_suspend_revoke_sessions_restore_and_owner_protection(client, owner_signed_in):
    c = create(client, owner_signed_in)
    with TestClient(client.app) as customer:
        register(customer, EMAIL)
        assert change(client, owner_signed_in, c, "status", suspended=True).status_code == 200
        assert not customer.get("/api/session").json()["authenticated"]
        credentials = {"email": EMAIL, "password": "Test-only passphrase 847!"}
        assert (
            customer.post("/api/auth/login", headers=HEADERS, json=credentials).status_code == 403
        )
        assert change(client, owner_signed_in, c, "status", suspended=False).status_code == 200
        assert (
            customer.post("/api/auth/login", headers=HEADERS, json=credentials).status_code == 200
        )
        assert change(client, owner_signed_in, c, "sessions").json()["revoked"] == 1
        assert not customer.get("/api/session").json()["authenticated"]
    own = client.get("/api/admin/crm/contacts?q=investor@example.com").json()["contacts"][0]
    for action, body in [
        ("status", {"suspended": True}),
        ("sessions", {}),
        ("access", {"action": "complimentary"}),
        ("email-action", {"purpose": "reset"}),
    ]:
        assert change(client, owner_signed_in, own, action, **body).status_code == 409
    assert client.get("/api/session").json()["is_owner"]


def test_profile_email_change_revokes_sessions_tokens_and_verification(client, owner_signed_in):
    c = create(client, owner_signed_in)
    with TestClient(client.app) as customer:
        register(customer, EMAIL)
        with client.app.state.factory() as db, db.begin():
            account = db.scalar(select(Account).where(Account.email == EMAIL))
            db.add(AccountEmail(account_id=account.id, verified_at=1))
            db.add(
                AccountAction(
                    token_hash="fixture-hash",
                    account_id=account.id,
                    purpose="reset",
                    expires_at=int(time.time()) + 60,
                )
            )
        response = client.patch(
            f"/api/admin/crm/contacts/{c['id']}/profile",
            headers=owner_signed_in,
            json={
                **PROFILE,
                "email": "corrected-fixture@example.com",
                "revision": row(client, c["id"])["revision"],
                "company": "Updated Fixture",
                "reason": "Correct typo in email",
            },
        )
        assert response.status_code == 200, response.text
        assert not customer.get("/api/session").json()["authenticated"]
        with client.app.state.factory() as db:
            assert db.scalar(select(Account).where(Account.email == EMAIL)) is None
            assert db.scalar(select(AccountAction)) is None
            assert db.scalar(select(AccountEmail)) is None
        assert not details(client, c)["verified"]
        assert not row(client, c["id"])["marketing_opt_in"]


def test_duplicate_email_stale_write_and_invalid_actions_are_atomic(client, owner_signed_in):
    c = create(client, owner_signed_in)
    assert (
        client.post(
            "/api/admin/crm/contacts",
            headers=owner_signed_in,
            json={**PROFILE, "email": EMAIL.upper()},
        ).status_code
        == 409
    )
    body = {"revision": c["revision"], "reason": "Fixture request", "action": "trial", "days": 7}
    url = f"/api/admin/crm/contacts/{c['id']}/access"
    assert client.post(url, headers=owner_signed_in, json=body).status_code == 200
    assert client.post(url, headers=owner_signed_in, json=body).status_code == 409
    current = row(client, c["id"])
    for days in (0, 366, 1.5, True, None):
        response = client.post(
            url,
            headers=owner_signed_in,
            json={**body, "revision": current["revision"], "days": days},
        )
        assert response.status_code == 422
    assert row(client, c["id"])["revision"] == current["revision"]
    assert change(client, owner_signed_in, c, "email-action", purpose="reset").status_code == 409


@pytest.mark.parametrize(
    "route,body",
    [
        ("access", {"action": "trial", "days": 30}),
        ("status", {"suspended": True}),
        ("sessions", {}),
        ("email-action", {"purpose": "reset"}),
    ],
)
def test_account_mutations_require_owner_and_csrf(client, owner_signed_in, route, body):
    c = create(client, owner_signed_in)
    payload = {"revision": c["revision"], "reason": "Fixture reason", **body}
    url = f"/api/admin/crm/contacts/{c['id']}/{route}"
    assert client.post(url, headers=HEADERS, json=payload).status_code == 403
    with TestClient(client.app) as outsider:
        assert outsider.post(url, headers=HEADERS, json=payload).status_code == 401
        register(outsider, "outsider-fixture@example.com")
        assert outsider.post(url, headers=HEADERS, json=payload).status_code == 403
    assert row(client, c["id"])["revision"] == c["revision"]


def test_no_secrets_or_fabricated_consent_and_mail_unavailable(client, owner_signed_in):
    assert (
        client.post(
            "/api/admin/crm/contacts",
            headers=owner_signed_in,
            json={**PROFILE, "email": EMAIL, "marketing_opt_in": True},
        ).status_code
        == 422
    )
    c = create(client, owner_signed_in)
    with TestClient(client.app) as customer:
        register(customer, EMAIL)
    result = details(client, c)
    assert not result["mail_enabled"]
    assert not {"password", "password_hash", "csrf", "token_hash", "customer_id"} & result.keys()
    assert change(client, owner_signed_in, c, "email-action", purpose="reset").status_code == 503
    with client.app.state.factory() as db:
        assert db.scalar(select(AccountAction)) is None


def test_v10_migration_retains_manual_contacts_and_is_repeatable(client, owner_signed_in):
    c = create(client, owner_signed_in)
    with client.app.state.factory() as db, db.begin():
        db.execute(update(SchemaVersion).values(version=10))
    engine = client.app.state.factory.kw["bind"]
    from landwolf.db import AccountRestriction

    AccountRestriction.__table__.drop(engine)
    AccountAdminAudit.__table__.drop(engine)
    crm_core.Reservation.__table__.drop(engine)
    initialize(engine)
    initialize(engine)
    assert row(client, c["id"])["email"] == EMAIL
    with client.app.state.factory() as db:
        assert db.scalar(select(SchemaVersion.version)) == 12


def test_paid_subscription_survives_trial_revoke(client, owner_signed_in, monkeypatch):
    from landwolf.db import BillingCustomer

    c = create(client, owner_signed_in)
    with TestClient(client.app) as customer:
        register(customer, EMAIL)
        with client.app.state.factory() as db, db.begin():
            account = db.scalar(select(Account).where(Account.email == EMAIL))
            db.add(
                BillingCustomer(
                    account_id=account.id,
                    customer_id="cus_fixture",
                    paid_until=int(time.time()) + 86400,
                    synced_at=int(time.time()),
                    subscription_status="active",
                )
            )
        client.app.state.settings.payments_enabled = True
        monkeypatch.setattr(
            billing, "refresh_customer", lambda s, a, c: s.get(BillingCustomer, a.id)
        )
        change(client, owner_signed_in, c, "access", action="trial", days=7)
        change(client, owner_signed_in, c, "access", action="revoke")
        state = customer.get("/api/billing/status").json()
        assert state["allowed"] and state["reason"] == "subscription"
