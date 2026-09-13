from pathlib import Path

def test_checkout_plan_allowlist_and_price_mapping():
    schema = Path("app/schemas.py").read_text()
    service = Path("app/services/billing.py").read_text()
    api = Path("app/api/billing.py").read_text()
    assert 'Literal["monthly", "annual"]' in schema
    assert "price_id_for_plan" in service
    assert "settings.stripe_monthly_price_id" in service
    assert "settings.stripe_annual_price_id" in service
    assert "body.plan" in api

def test_frontend_exposes_both_subscription_choices():
    html = Path("app/static/index.html").read_text()
    js = Path("app/static/app.js").read_text()
    assert "$29/month" in html
    assert "$299/year" in html
    assert "Save $49/year" in html
    assert "JSON.stringify({plan})" in js

def test_sandbox_env_has_created_stripe_price_ids():
    env = Path(".env.sandbox.example").read_text()
    assert "STRIPE_MONTHLY_PRICE_ID=price_1UF0dePh6su6RDu3UuTVDEYx" in env
    assert "STRIPE_ANNUAL_PRICE_ID=price_1UF0dlPh6su6RDu3ydcc9vDU" in env
    assert "STRIPE_SECRET_KEY=sk_test_replace_me" in env

def test_webhook_helper_registers_required_events():
    script = Path("scripts/register_stripe_webhook.py").read_text()
    for event in [
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.payment_failed",
        "invoice.paid",
    ]:
        assert event in script
    assert "/api/billing/webhook" in script
    assert 'parsed.scheme != "https"' in script
