"""Financial boundaries use synthetic Stripe; no real customers are charged."""

import copy
import time

import pytest
from test_feedback import ANSWERS
from test_live_billing import paid_app as billing_fixture  # noqa: F401

from landwolf import billing, recovery, trials
from landwolf.db import AccountEmail, FeedbackTrial, TrialResponse


@pytest.fixture
def trial_app(billing_fixture, monkeypatch):  # noqa: F811
    client, owner, user, headers, fake = billing_fixture
    settings = client.app.state.settings
    settings.feedback_trial_launch_at = user.created_at
    settings.mail_provider = "gmail"
    settings.mail_from = "support.landwolf@gmail.com"
    sent = []

    async def send(self, email, subject, text, message_id):
        sent.append((email, subject, text, message_id))

    monkeypatch.setattr(recovery.Mailer, "send_text", send)
    with client.app.state.factory() as session:
        session.add(AccountEmail(account_id=user.id, verified_at=int(time.time())))
        session.commit()
    original = fake.call
    fake.setups = {}
    fake.subscription_creations = 0
    fake.payment_attempts = 0
    fake.lost_payment = False
    fake.bad_descriptor = False
    fake.descriptor = None
    fake.invoice_total = 2900
    fake.lost_conversion = False

    def call(api, method, path, fields=None, *, idempotency_key=None):
        if path == "/checkout/sessions" and fields and fields.get("mode") == "setup":
            fake.calls.append((method, path, fields, idempotency_key))
            if idempotency_key not in fake.setups:
                fake.setups[idempotency_key] = {
                    "id": "cs_live_trial",
                    "livemode": True,
                    "mode": "setup",
                    "customer": "cus_fixture",
                    "client_reference_id": user.id,
                    "status": "open",
                    "url": "https://checkout.stripe.com/c/pay/trial",
                    "setup_intent": "seti_fixture",
                }
            return copy.deepcopy(fake.setups[idempotency_key])
        if path == "/checkout/sessions/cs_live_trial":
            return copy.deepcopy(next(iter(fake.setups.values())))
        if path == "/setup_intents/seti_fixture":
            return {
                "id": "seti_fixture",
                "livemode": True,
                "status": "succeeded",
                "customer": "cus_fixture",
                "payment_method": "pm_fixture",
            }
        if method == "POST" and path == "/subscriptions":
            fake.calls.append((method, path, fields, idempotency_key))
            fake.subscription_creations += 1
            fake.rows = [
                {
                    "id": "sub_trial",
                    "livemode": True,
                    "customer": "cus_fixture",
                    "status": "incomplete",
                    "latest_invoice": "in_trial",
                    "cancel_at_period_end": False,
                    "metadata": {
                        "app": "landwolf",
                        "account_id": user.id,
                        "feedback_trial": fields["metadata[feedback_trial]"],
                    },
                    "collection_method": "charge_automatically",
                    "items": {
                        "has_more": False,
                        "data": [
                            {
                                "price": {"id": "price_monthly"},
                                "quantity": 1,
                                "current_period_end": int(time.time()) + 30 * trials.DAY,
                            }
                        ],
                    },
                }
            ]
            if fake.lost_conversion:
                fake.lost_conversion = False
                raise billing.unavailable()
            return copy.deepcopy(fake.rows[0])
        if path == "/invoices/in_trial":
            if method == "POST":
                fake.descriptor = None if fake.bad_descriptor else fields["statement_descriptor"]
            return {
                "id": "in_trial",
                "livemode": True,
                "customer": "cus_fixture",
                "status": "open",
                "currency": "usd",
                "total": fake.invoice_total,
                "amount_due": fake.invoice_total,
                "statement_descriptor": fake.descriptor,
                "parent": {"subscription_details": {"subscription": "sub_trial"}},
                "lines": {
                    "has_more": False,
                    "data": [{"pricing": {"price_details": {"price": "price_monthly"}}}],
                },
            }
        if path == "/invoices/in_trial/pay":
            assert fake.descriptor == "LANDWOLF* TRIAL OVER"
            fake.payment_attempts += 1
            fake.rows[0]["status"] = "active"
            if fake.lost_payment:
                fake.lost_payment = False
                raise billing.unavailable()
            return {"status": "paid"}
        if method == "DELETE" and path == "/subscriptions/sub_trial":
            fake.rows[0]["status"] = "incomplete_expired"
            return copy.deepcopy(fake.rows[0])
        if method == "POST" and path == "/subscriptions/sub_trial":
            fake.rows[0]["cancel_at_period_end"] = True
            return copy.deepcopy(fake.rows[0])
        return original(api, method, path, fields, idempotency_key=idempotency_key)

    monkeypatch.setattr(billing.StripeAPI, "call", lambda api, *a, **k: call(api, *a, **k))
    return client, owner, user, headers, fake, sent


def enroll(context):
    client, _, user, headers, fake, _ = context
    result = client.post(
        "/api/trial/checkout",
        headers=headers,
        json={"terms_version": trials.TERMS_VERSION, "accepted_recurring_terms": True},
    )
    assert result.status_code == 200, result.text
    next(iter(fake.setups.values()))["status"] = "complete"
    result = client.post("/api/billing/refresh", headers=headers, json={})
    assert result.status_code == 200, result.text
    assert result.json()["reason"] == "feedback_trial"
    with client.app.state.factory() as session:
        return session.get(FeedbackTrial, user.id).started_at


def tick(context, now, monkeypatch):
    monkeypatch.setattr(trials.time, "time", lambda: now)
    trials.tick(context[0].app.state.factory, context[0].app.state.settings)


def row(context):
    with context[0].app.state.factory() as session:
        return session.get(FeedbackTrial, context[2].id)


def test_consent_verification_setup_and_no_immediate_charge(trial_app):
    client, _, user, headers, fake, _ = trial_app
    for value in (False, 1, "true", None):
        result = client.post(
            "/api/trial/checkout",
            headers=headers,
            json={"terms_version": trials.TERMS_VERSION, "accepted_recurring_terms": value},
        )
        assert result.status_code == 422
    assert fake.customer_creations == 0
    with client.app.state.factory() as session:
        session.delete(session.get(AccountEmail, user.id))
        session.commit()
    assert (
        client.post(
            "/api/trial/checkout",
            headers=headers,
            json={"terms_version": trials.TERMS_VERSION, "accepted_recurring_terms": True},
        ).status_code
        == 409
    )
    assert fake.customer_creations == 0


def test_missed_feedback_requires_notice_and_full_grace_then_one_subscription(
    trial_app, monkeypatch
):
    start = enroll(trial_app)
    tick(trial_app, start + 30 * trials.DAY, monkeypatch)
    current = row(trial_app)
    assert current.state == "notice"
    assert current.charge_at >= start + 37 * trials.DAY
    assert trial_app[4].subscription_creations == 0
    tick(trial_app, current.charge_at - 1, monkeypatch)
    assert trial_app[4].subscription_creations == 0
    tick(trial_app, current.charge_at, monkeypatch)
    assert row(trial_app).state == "subscribed"
    assert trial_app[4].subscription_creations == 1
    assert trial_app[0].get("/api/billing/status").json()["allowed"] is True
    tick(trial_app, current.charge_at + 3600, monkeypatch)
    assert trial_app[4].subscription_creations == 1
    fields = next(c[2] for c in trial_app[4].calls if c[:2] == ("POST", "/subscriptions"))
    assert fields["items[0][price]"] == "price_monthly"
    assert fields["payment_behavior"] == "default_incomplete"
    assert trial_app[4].payment_attempts == 1
    assert "backdate_start_date" not in fields
    assert "payment_method_types" not in fields


@pytest.mark.parametrize("day", [30, 60, 90])
def test_feedback_during_notice_prevents_conversion(trial_app, monkeypatch, day):
    start = enroll(trial_app)
    with trial_app[0].app.state.factory() as session:
        for earlier in trials.DAYS:
            if earlier < day:
                session.add(
                    TrialResponse(
                        account_id=trial_app[2].id, day=earlier, answers=ANSWERS, submitted_at=start
                    )
                )
        session.commit()
    tick(trial_app, start + day * trials.DAY, monkeypatch)
    deadline = row(trial_app).charge_at
    client, _, _, headers, _, _ = trial_app
    result = client.post(
        "/api/trial/feedback", headers=headers, json={"day": day, "answers": ANSWERS}
    )
    assert result.status_code == 200, result.text
    tick(trial_app, deadline, monkeypatch)
    assert trial_app[4].subscription_creations == 0
    assert row(trial_app).state == ("completed" if day == 90 else "active")


def test_cancel_and_email_failure_never_charge(trial_app, monkeypatch):
    start = enroll(trial_app)

    async def fail(*args):
        raise RuntimeError("transport unavailable")

    monkeypatch.setattr(recovery.Mailer, "send_text", fail)
    tick(trial_app, start + 30 * trials.DAY, monkeypatch)
    tick(trial_app, start + 38 * trials.DAY, monkeypatch)
    assert row(trial_app).charge_at is None
    assert trial_app[4].subscription_creations == 0
    client, _, _, headers, _, _ = trial_app
    assert client.post("/api/trial/cancel", headers=headers, json={}).status_code == 200
    tick(trial_app, start + 60 * trials.DAY, monkeypatch)
    assert trial_app[4].subscription_creations == 0


def test_outage_after_notice_blocks_late_charge(trial_app, monkeypatch):
    start = enroll(trial_app)
    tick(trial_app, start + 30 * trials.DAY, monkeypatch)
    deadline = row(trial_app).charge_at
    tick(trial_app, deadline + trials.DAY + 1, monkeypatch)
    assert row(trial_app).state == "blocked"
    assert trial_app[4].subscription_creations == 0


def test_lost_conversion_response_reconciles_without_duplicate(trial_app, monkeypatch):
    start = enroll(trial_app)
    tick(trial_app, start + 30 * trials.DAY, monkeypatch)
    deadline = row(trial_app).charge_at
    trial_app[4].lost_conversion = True
    tick(trial_app, deadline, monkeypatch)
    assert row(trial_app).state == "converting"
    tick(trial_app, deadline + 3600, monkeypatch)
    assert row(trial_app).state == "subscribed"
    assert trial_app[4].subscription_creations == 1


def test_early_and_invalid_feedback_cannot_preempt_requirements(trial_app):
    enroll(trial_app)
    client, _, _, headers, _, _ = trial_app
    assert (
        client.post(
            "/api/trial/feedback", headers=headers, json={"day": 30, "answers": ANSWERS}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/trial/feedback", headers=headers, json={"day": 31, "answers": ANSWERS}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/trial/feedback", headers=headers, json={"day": 30, "answers": {}}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/trial/feedback",
            headers={"Origin": "http://evil.example"},
            json={"day": 30, "answers": ANSWERS},
        ).status_code
        == 403
    )


def test_old_accounts_and_crm_history_are_excluded(trial_app):
    client, _, user, _, _, _ = trial_app
    settings = client.app.state.settings
    with client.app.state.factory() as session:
        settings.feedback_trial_launch_at = user.created_at + 1
        assert not trials.eligible(session, user, settings)
        settings.feedback_trial_launch_at = user.created_at
        settings.pilot_invite_emails = (user.email,)
        assert not trials.eligible(session, user, settings)


def test_crm_grant_during_notice_stops_conversion(trial_app, monkeypatch):
    from landwolf.crm_access import apply_grant

    start = enroll(trial_app)
    tick(trial_app, start + 30 * trials.DAY, monkeypatch)
    deadline = row(trial_app).charge_at
    client, owner, user, _, fake, _ = trial_app
    with client.app.state.factory() as session:
        billing.lock_account(session, user.id)
        apply_grant(session, user, owner.id, "Owner-approved trial fixture", 90)
        session.commit()
    tick(trial_app, deadline, monkeypatch)
    assert row(trial_app).state == "cancelled"
    assert fake.subscription_creations == 0
    assert client.get("/api/billing/status").json()["reason"] == "complimentary"


def test_cancel_after_notice_is_final(trial_app, monkeypatch):
    start = enroll(trial_app)
    tick(trial_app, start + 30 * trials.DAY, monkeypatch)
    deadline = row(trial_app).charge_at
    client, _, _, headers, fake, _ = trial_app
    assert client.post("/api/trial/cancel", headers=headers, json={}).status_code == 200
    tick(trial_app, deadline, monkeypatch)
    assert fake.subscription_creations == 0
    assert row(trial_app).state == "cancelled"
    assert not client.get("/api/billing/status").json()["allowed"]


def test_cancel_after_lost_response_stops_renewal_not_a_second_charge(trial_app, monkeypatch):
    start = enroll(trial_app)
    tick(trial_app, start + 30 * trials.DAY, monkeypatch)
    deadline = row(trial_app).charge_at
    trial_app[4].lost_conversion = True
    tick(trial_app, deadline, monkeypatch)
    client, _, _, headers, fake, _ = trial_app
    assert client.post("/api/trial/cancel", headers=headers, json={}).status_code == 200
    tick(trial_app, deadline + 3600, monkeypatch)
    assert fake.subscription_creations == 1
    assert fake.rows[0]["status"] == "incomplete_expired"


def test_setup_complete_url_cannot_grant_access(trial_app):
    client, _, _, headers, fake, _ = trial_app
    assert (
        client.post(
            "/api/trial/checkout",
            headers=headers,
            json={"terms_version": trials.TERMS_VERSION, "accepted_recurring_terms": True},
        ).status_code
        == 200
    )
    assert not client.post("/api/billing/refresh", headers=headers, json={}).json()["allowed"]
    assert fake.subscription_creations == 0
    assert row(trial_app).state == "setup"


def test_notice_delivery_failure_does_not_start_countdown(trial_app, monkeypatch):
    start = enroll(trial_app)
    tick(trial_app, start, monkeypatch)

    async def fail(*args):
        raise RuntimeError("mail delivery unavailable")

    monkeypatch.setattr(recovery.Mailer, "send_text", fail)
    tick(trial_app, start + 30 * trials.DAY, monkeypatch)
    tick(trial_app, start + 38 * trials.DAY, monkeypatch)
    assert row(trial_app).state == "active"
    assert row(trial_app).charge_at is None
    assert trial_app[4].subscription_creations == 0


def test_unexpected_invoice_amount_cannot_be_charged(trial_app, monkeypatch):
    start = enroll(trial_app)
    tick(trial_app, start + 30 * trials.DAY, monkeypatch)
    deadline = row(trial_app).charge_at
    trial_app[4].invoice_total = 5800
    tick(trial_app, deadline, monkeypatch)
    assert row(trial_app).state == "blocked"
    assert trial_app[4].payment_attempts == 0
    assert trial_app[0].get("/api/billing/status").json()["allowed"] is False


def test_new_facebook_campaign_uses_conditional_offer_not_legacy_invitation(trial_app):
    from sqlalchemy import select

    from landwolf.crm_core import Contact
    from landwolf.db import FeedbackEnrollment

    client, _, user, _, _, _ = trial_app
    with client.app.state.factory() as session, session.begin():
        contact = session.scalar(select(Contact).where(Contact.external_id == user.id))
        contact.tags = ["facebook-90-day-feedback"]
    value = client.get("/api/feedback").json()
    assert value["pilot_reserved"] is False
    assert value["self_service_trial"]["eligible"] is True
    with client.app.state.factory() as session:
        assert session.get(FeedbackEnrollment, user.id) is None


def test_self_service_feedback_is_visible_only_in_owner_report(trial_app, monkeypatch):
    from test_live_billing import login

    client, owner, user, headers, _, _ = trial_app
    start = enroll(trial_app)
    tick(trial_app, start + 30 * trials.DAY, monkeypatch)
    assert (
        client.post(
            "/api/trial/feedback", headers=headers, json={"day": 30, "answers": ANSWERS}
        ).status_code
        == 200
    )
    assert client.get("/api/admin/feedback/responses").status_code == 403
    login(client, owner.email)
    result = client.get("/api/admin/feedback/responses")
    assert result.status_code == 200
    response = next(r for r in result.json()["responses"] if r["account_id"] == user.id)
    assert response["survey_key"] == "self-service-day30"
    assert response["answers"]["usage"] == ANSWERS["usage"]


def test_lost_payment_response_never_charges_twice(trial_app, monkeypatch):
    start = enroll(trial_app)
    tick(trial_app, start + 30 * trials.DAY, monkeypatch)
    deadline = row(trial_app).charge_at
    trial_app[4].lost_payment = True
    tick(trial_app, deadline, monkeypatch)
    assert row(trial_app).state == "converting"
    tick(trial_app, deadline + 3600, monkeypatch)
    assert row(trial_app).state == "subscribed"
    assert trial_app[4].payment_attempts == 1
    assert trial_app[4].subscription_creations == 1


def test_unverified_statement_descriptor_withholds_payment(trial_app, monkeypatch):
    start = enroll(trial_app)
    tick(trial_app, start + 30 * trials.DAY, monkeypatch)
    deadline = row(trial_app).charge_at
    trial_app[4].bad_descriptor = True
    tick(trial_app, deadline, monkeypatch)
    assert trial_app[4].payment_attempts == 0
    assert row(trial_app).state == "converting"


def test_schema_11_upgrade_is_additive_and_repeatable(trial_app):
    from sqlalchemy import inspect, select, update

    from landwolf.db import Account, SchemaVersion, TrialMessage, initialize

    client, _, user, _, _, _ = trial_app
    engine = client.app.state.factory.kw["bind"]
    with client.app.state.factory() as session, session.begin():
        original = session.get(Account, user.id).password_hash
        session.execute(update(SchemaVersion).values(version=11))
    TrialMessage.__table__.drop(engine)
    TrialResponse.__table__.drop(engine)
    FeedbackTrial.__table__.drop(engine)
    initialize(engine)
    initialize(engine)
    assert inspect(engine).has_table("lw2_trial_messages")
    with client.app.state.factory() as session:
        assert session.scalar(select(SchemaVersion.version)) == 13
        assert session.get(Account, user.id).password_hash == original
