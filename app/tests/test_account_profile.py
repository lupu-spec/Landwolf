"""Real self-service CRM writes and mailbox reset, with strict identity boundaries."""

import pytest
from conftest import register
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from test_recovery import mailer as mailer

from landwolf import auth, crm_core
from landwolf.crm_core import Activity, Contact, Profile
from landwolf.db import Account, AccountAction, AccountRestriction


def payload(client, **changes):
    profile = client.get("/api/account/profile").json()["profile"]
    return {key: value for key, value in {**profile, **changes}.items() if key != "email"}


def test_self_profile_reads_only_own_allowlisted_fields_and_updates_crm(client, signed_in):
    with client.app.state.factory() as session, session.begin():
        contact = session.scalar(select(Contact))
        contact.tags = ["Owner private tag"]
        contact.lifecycle = "qualified"
        contact.follow_up_on = "2026-12-01"
        crm_core.record_activity(session, contact.id, "owner-fixture", "note", "Private owner note")
    # Account support remains available without paid property-search access.
    client.app.state.settings.payments_enabled = True
    before = client.get("/api/account/profile")
    assert before.status_code == 200
    profile = before.json()["profile"]
    assert set(profile) == set(Profile.model_fields) | {"email", "revision"}
    assert "Private owner" not in before.text and "Owner private" not in before.text
    body = payload(
        client, full_name="Updated Fixture", company="Fixture Works", phone="+1 212 555 0100"
    )
    saved = client.patch("/api/account/profile", json=body, headers=signed_in)
    assert saved.status_code == 200
    assert saved.json()["profile"]["company"] == "Fixture Works"
    assert saved.json()["profile"]["revision"] == profile["revision"] + 1
    with client.app.state.factory() as session:
        row = session.scalar(select(Contact))
        assert row.full_name == "Updated Fixture" and row.phone == "+1 212 555 0100"
        assert row.tags == ["Owner private tag"] and row.lifecycle == "qualified"
        assert row.follow_up_on == "2026-12-01"
        event = session.scalar(select(Activity).where(Activity.kind == "profile_self_updated"))
        assert event.actor_id == row.external_id
        assert "company" in event.text and "Fixture Works" not in event.text


def test_self_profile_consent_can_be_opted_in_and_out(client, signed_in):
    for consent in (True, False):
        response = client.patch(
            "/api/account/profile",
            json=payload(client, marketing_opt_in=consent),
            headers=signed_in,
        )
        assert response.status_code == 200
        with client.app.state.factory() as session:
            row = session.scalar(select(Contact))
            assert row.marketing_opt_in is consent
            assert row.consent_version == crm_core.CONSENT_VERSION
            assert row.consent_recorded_at > 0


@pytest.mark.parametrize(
    "extra",
    [
        {"id": "another-contact"},
        {"account_id": "another-account"},
        {"email": "other@example.com"},
        {"lifecycle": "customer"},
        {"tags": ["trial_user"]},
        {"project_id": "other-project"},
        {"is_owner": True},
        {"delete": True},
        {"password": "Synthetic secret 948!"},
    ],
)
def test_self_service_rejects_identity_and_admin_fields(client, signed_in, extra):
    before = client.get("/api/account/profile").json()
    response = client.patch(
        "/api/account/profile", json={**payload(client), **extra}, headers=signed_in
    )
    assert response.status_code == 422
    assert client.get("/api/account/profile").json() == before


@pytest.mark.parametrize(
    "change",
    [
        {"full_name": " "},
        {"full_name": "x" * 121},
        {"phone": "invalid"},
        {"industry": "arbitrary"},
        {"primary_use": ""},
        {"revision": True},
        {"marketing_opt_in": "yes"},
        {"job_title": "bad\x00input"},
    ],
)
def test_self_profile_invalid_input_is_atomic(client, signed_in, change):
    before = client.get("/api/account/profile").json()
    response = client.patch(
        "/api/account/profile", json=payload(client, **change), headers=signed_in
    )
    assert response.status_code == 422
    assert client.get("/api/account/profile").json() == before


def test_stale_profile_and_database_failure_do_not_overwrite(client, signed_in, monkeypatch):
    body = payload(client, company="First write")
    assert client.patch("/api/account/profile", json=body, headers=signed_in).status_code == 200
    assert (
        client.patch(
            "/api/account/profile", json={**body, "company": "Stale write"}, headers=signed_in
        ).status_code
        == 409
    )

    def fail(*args):
        raise SQLAlchemyError("Synthetic audit failure")

    monkeypatch.setattr(crm_core, "record_activity", fail)
    response = client.patch(
        "/api/account/profile", json=payload(client, company="Rolled back"), headers=signed_in
    )
    assert response.status_code == 503
    assert "Synthetic audit" not in response.text
    assert client.get("/api/account/profile").json()["profile"]["company"] == "First write"


def test_profile_is_bound_to_session_not_email_or_query(client, signed_in):
    first = client.get("/api/account/profile").json()["profile"]
    second_headers = register(client, "second-profile@example.com")
    own = client.get("/api/account/profile?email=investor@example.com&id=another-contact").json()[
        "profile"
    ]
    assert own["email"] == "second-profile@example.com"
    assert (
        client.patch(
            "/api/account/profile",
            json=payload(client, company="Second company"),
            headers=second_headers,
        ).status_code
        == 200
    )
    with client.app.state.factory() as session:
        original = session.scalar(select(Contact).where(Contact.email == first["email"]))
        assert original.company == "" and original.revision == first["revision"]
    assert client.delete("/api/account/profile", headers=second_headers).status_code == 405
    assert client.get("/api/account/profile").json()["profile"]["company"] == "Second company"


def test_self_service_requires_session_csrf_and_trusted_origin(client, signed_in):
    body = payload(client, company="Must not save")
    no_csrf = {key: value for key, value in signed_in.items() if key != "X-CSRF-Token"}
    for headers in (no_csrf, {**signed_in, "Origin": "https://evil.example"}):
        assert client.patch("/api/account/profile", json=body, headers=headers).status_code == 403
        assert (
            client.post("/api/account/password-reset", json={}, headers=headers).status_code == 403
        )
    client.cookies.clear()
    assert client.get("/api/account/profile").status_code == 401
    assert client.patch("/api/account/profile", json=body, headers=signed_in).status_code == 401
    assert client.post("/api/account/password-reset", json={}, headers=signed_in).status_code == 401


def test_suspended_account_cannot_use_profile_or_signed_in_reset(client, signed_in):
    body = payload(client)
    with client.app.state.factory() as session, session.begin():
        account = session.scalar(select(Account))
        session.add(
            AccountRestriction(
                account_id=account.id,
                suspended=True,
                reason="Fixture hold",
                updated_by=account.id,
                updated_at=1,
            )
        )
    assert client.get("/api/account/profile").status_code == 403
    assert client.patch("/api/account/profile", json=body, headers=signed_in).status_code == 403
    assert client.post("/api/account/password-reset", json={}, headers=signed_in).status_code == 403


def test_chat_reset_uses_stored_email_and_requires_mailbox_token(client, signed_in, mailer):
    with client.app.state.factory() as session:
        old_hash = session.scalar(select(Account.password_hash))
    assert (
        client.post(
            "/api/account/password-reset", json={"email": "other@example.com"}, headers=signed_in
        ).status_code
        == 422
    )
    response = client.post("/api/account/password-reset", json={}, headers=signed_in)
    assert response.status_code == 202
    email, purpose, token = mailer.messages[0]
    assert email == "investor@example.com" and purpose == "reset"
    assert token not in response.text
    with client.app.state.factory() as session:
        assert session.scalar(select(Account.password_hash)) == old_hash
        assert session.scalar(select(AccountAction)).token_hash == auth.digest(token)
    password = "Replacement fixture passphrase 843!"
    assert (
        client.post(
            "/api/auth/reset-password", json={"password": password}, headers=signed_in
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/auth/reset-password",
            json={"password": password, "token": token},
            headers=signed_in,
        ).status_code
        == 200
    )
    assert client.get("/api/account/profile").status_code == 401
    assert (
        client.post(
            "/api/auth/reset-password",
            json={"password": password, "token": token},
            headers=signed_in,
        ).status_code
        == 400
    )


def test_chat_reset_delivery_off_and_rate_limit_are_explicit(client, signed_in, mailer):
    mailer.enabled = False
    assert client.post("/api/account/password-reset", json={}, headers=signed_in).status_code == 503
    mailer.enabled = True
    for _ in range(2):
        assert (
            client.post("/api/account/password-reset", json={}, headers=signed_in).status_code
            == 202
        )
    assert client.post("/api/account/password-reset", json={}, headers=signed_in).status_code == 429
