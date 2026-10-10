"""Facebook campaign must create a verified, consent-based trial without Stripe."""

import time

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from landwolf.crm_core import Contact
from landwolf.db import Account, AccountEmail, BillingCustomer, FeedbackAudit, FeedbackEnrollment
from test_feedback import ACCEPT

ORIGIN = {"Origin": "http://testserver", "X-LandWolf-Client": "web"}
PASSWORD = "Test-only passphrase 847!"
CAMPAIGN = "facebook-90-day-feedback"


def _signup(client: TestClient, email: str, *, campaign: str | None = None):
    body = {
        "email": email,
        "password": PASSWORD,
        "profile": {"full_name": "Campaign Fixture", "primary_use": "investing"},
    }
    if campaign is not None:
        body["campaign"] = campaign
    return client.post("/api/auth/register", headers=ORIGIN, json=body)


def _owner(client: TestClient) -> None:
    response = _signup(client, "campaign-owner@example.com")
    assert response.status_code == 201, response.text
    with client.app.state.factory() as session:
        owner = session.scalar(select(Account).where(Account.email == "campaign-owner@example.com"))
        assert owner is not None
        client.app.state.settings.owner_account_id = owner.id
    assert client.post(
        "/api/auth/logout",
        headers={**ORIGIN, "X-CSRF-Token": response.json()["csrf"]},
        json={},
    ).status_code == 200


def test_campaign_verified_email_and_feedback_required_for_access(client: TestClient):
    _owner(client)
    client.app.state.settings.payments_enabled = True
    response = _signup(client, "campaign-user@example.com", campaign=CAMPAIGN)
    assert response.status_code == 201, response.text
    headers = {**ORIGIN, "X-CSRF-Token": response.json()["csrf"]}
    with client.app.state.factory() as session:
        account = session.scalar(select(Account).where(Account.email == "campaign-user@example.com"))
        assert account is not None
        contact = session.scalar(
            select(Contact).where(Contact.project_id == "landwolf", Contact.external_id == account.id)
        )
        assert contact is not None
        assert CAMPAIGN in contact.tags
        assert not contact.marketing_opt_in
        assert session.get(BillingCustomer, account.id) is None

    # A Facebook URL or arbitrary email string is NOT proof of mailbox control.
    reserved = client.get("/api/feedback")
    assert reserved.status_code == 200
    assert reserved.json()["pilot_reserved"] is True
    assert reserved.json()["state"] == "none"
    assert client.post("/api/feedback/accept", headers=headers, json=ACCEPT).status_code == 403
    assert client.get("/api/billing/status").json()["allowed"] is False

    with client.app.state.factory() as session, session.begin():
        session.add(AccountEmail(account_id=account.id, verified_at=int(time.time())))

    offer = client.get("/api/feedback")
    assert offer.status_code == 200, offer.text
    assert offer.json()["state"] == "invited"
    assert client.get("/api/billing/status").json()["allowed"] is False
    accepted = client.post("/api/feedback/accept", headers=headers, json=ACCEPT)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["state"] == "active"
    assert accepted.json()["expires_at"] > accepted.json()["accepted_at"] + 80 * 86400
    allowed = client.get("/api/billing/status").json()
    assert allowed["allowed"] is True
    assert allowed["reason"] == "pilot"
    assert allowed["subscription_status"] == "none"
    assert client.get("/api/feedback").json()["expires_at"] == accepted.json()["expires_at"]

    with client.app.state.factory() as session:
        assert session.get(BillingCustomer, account.id) is None
        assert session.scalar(select(func.count()).select_from(FeedbackEnrollment)) == 1
        assert session.scalar(
            select(func.count()).select_from(FeedbackAudit).where(FeedbackAudit.action == "invite")
        ) == 1


def test_bad_campaign_is_rejected_and_normal_signup_cannot_claim(client: TestClient):
    _owner(client)
    bad = _signup(client, "invalid-campaign@example.com", campaign="unrecognized")
    assert bad.status_code == 422
    normal = _signup(client, "ordinary@example.com")
    assert normal.status_code == 201, normal.text
    with client.app.state.factory() as session, session.begin():
        account = session.scalar(select(Account).where(Account.email == "ordinary@example.com"))
        assert account is not None
        session.add(AccountEmail(account_id=account.id, verified_at=int(time.time())))
    assert client.get("/api/feedback").json()["pilot_reserved"] is False
    assert client.get("/api/feedback").json()["state"] == "none"
    assert client.post(
        "/api/feedback/accept",
        headers={**ORIGIN, "X-CSRF-Token": normal.json()["csrf"]},
        json=ACCEPT,
    ).status_code == 403


def test_campaign_requires_new_registration_not_existing_login(client: TestClient):
    _owner(client)
    assert _signup(client, "existing@example.com").status_code == 201
    response = client.post(
        "/api/auth/login",
        headers=ORIGIN,
        json={"email": "existing@example.com", "password": PASSWORD, "campaign": CAMPAIGN},
    )
    assert response.status_code == 422
    with client.app.state.factory() as session:
        contact = session.scalar(select(Contact).where(Contact.email == "existing@example.com"))
        assert contact is not None and CAMPAIGN not in (contact.tags or [])
