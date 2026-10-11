from pathlib import Path

def test_landwolf_domain_checkout_urls():
    env = Path(".env.sandbox.example").read_text()
    assert "STRIPE_SUCCESS_URL=https://landwolf.ai/?checkout=success" in env
    assert "STRIPE_CANCEL_URL=https://landwolf.ai/?checkout=cancel" in env

def test_landwolf_domain_webhook_registration_helper():
    script = Path("scripts/register_landwolf_ai_webhook.py").read_text()
    assert 'url="https://landwolf.ai/api/billing/webhook"' in script
    assert '"customer.subscription.updated"' in script
    assert '"customer.subscription.deleted"' in script
