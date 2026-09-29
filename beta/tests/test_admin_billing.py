"""Authorization and transaction regressions for complimentary billing access."""

import time

from conftest import register
from fastapi.testclient import TestClient
from sqlalchemy import select

from landwolf.db import Account, AdminAuditLog, BillingExemption


def owner_and_user(client: TestClient):
    owner_headers = register(client, "owner@example.com")
    with client.app.state.factory() as session:
        owner = session.scalar(select(Account).where(Account.email == "owner@example.com"))
        assert owner is not None
        client.app.state.settings.owner_account_id = owner.id
    client.post("/api/auth/logout", headers=owner_headers, json={})
    user_headers = register(client, "customer@example.com")
    with client.app.state.factory() as session:
        user = session.scalar(select(Account).where(Account.email == "customer@example.com"))
        assert user is not None
    client.post("/api/auth/logout", headers=user_headers, json={})
    login = client.post(
        "/api/auth/login",
        headers={"Origin": "http://testserver", "X-LandWolf-Client": "web"},
        json={"email": "owner@example.com", "password": "Test-only passphrase 847!"},
    )
    assert login.status_code == 200
    owner_headers = {
        "Origin": "http://testserver",
        "X-LandWolf-Client": "web",
        "X-CSRF-Token": login.json()["csrf"],
    }
    return owner, user, owner_headers


def test_non_owner_is_denied_admin_api(client: TestClient):
    headers = register(client, "ordinary@example.com")
    response = client.get("/api/admin/accounts")
    assert response.status_code == 403
    response = client.post(
        "/api/admin/accounts/not-an-account/complimentary-access",
        headers=headers,
        json={"reason": "no"},
    )
    assert response.status_code == 403


def test_grant_revoke_and_audit_are_atomic(client: TestClient):
    owner, user, headers = owner_and_user(client)
    grant = client.post(
        f"/api/admin/accounts/{user.id}/complimentary-access",
        headers=headers,
        json={"reason": "Early tester"},
    )
    assert grant.status_code == 201, grant.text
    assert grant.json()["billing_exempt"] is True
    with client.app.state.factory() as session:
        exemption = session.scalar(
            select(BillingExemption).where(BillingExemption.account_id == user.id)
        )
        assert exemption is not None and exemption.status == "active"
        events = session.scalars(select(AdminAuditLog)).all()
        assert len(events) == 1
        assert events[0].actor_account_id == owner.id
        assert events[0].action == "billing_exemption_granted"

    duplicate = client.post(
        f"/api/admin/accounts/{user.id}/complimentary-access",
        headers=headers,
        json={},
    )
    assert duplicate.status_code == 409

    revoke = client.request(
        "DELETE",
        f"/api/admin/accounts/{user.id}/complimentary-access",
        headers=headers,
        json={"reason": "Tester period complete"},
    )
    assert revoke.status_code == 200
    with client.app.state.factory() as session:
        exemption = session.scalar(
            select(BillingExemption).where(BillingExemption.account_id == user.id)
        )
        assert exemption is not None and exemption.status == "revoked"
        events = session.scalars(
            select(AdminAuditLog).order_by(AdminAuditLog.created_at, AdminAuditLog.action)
        ).all()
        assert len(events) == 2
        assert {event.action for event in events} == {
            "billing_exemption_granted",
            "billing_exemption_revoked",
        }

    regrant = client.post(
        f"/api/admin/accounts/{user.id}/complimentary-access",
        headers=headers,
        json={"reason": "Partner"},
    )
    assert regrant.status_code == 201
    with client.app.state.factory() as session:
        rows = session.scalars(
            select(BillingExemption).where(BillingExemption.account_id == user.id)
        ).all()
        assert len(rows) == 2
        assert sum(row.status == "active" for row in rows) == 1


def test_expiration_and_owner_are_defensive(client: TestClient):
    owner, user, headers = owner_and_user(client)
    owner_change = client.post(
        f"/api/admin/accounts/{owner.id}/complimentary-access",
        headers=headers,
        json={},
    )
    assert owner_change.status_code == 409
    past = client.post(
        f"/api/admin/accounts/{user.id}/complimentary-access",
        headers=headers,
        json={"expires_at": int(time.time()) - 1},
    )
    assert past.status_code == 422
    session_info = client.get("/api/session")
    assert session_info.status_code == 200
    assert session_info.json()["is_owner"] is True
    assert session_info.json()["access_override"] == "owner"


def test_admin_reads_are_owner_only_and_bounded(client: TestClient):
    owner, user, headers = owner_and_user(client)
    client.post(
        f"/api/admin/accounts/{user.id}/complimentary-access",
        headers=headers,
        json={"reason": "QA"},
    )
    accounts = client.get("/api/admin/accounts")
    assert accounts.status_code == 200
    target = next(row for row in accounts.json()["accounts"] if row["id"] == user.id)
    assert target["billing_exempt"] is True
    audit = client.get("/api/admin/audit")
    assert audit.status_code == 200
    assert audit.json()["events"][0]["action"] == "billing_exemption_granted"
