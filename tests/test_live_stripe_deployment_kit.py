from pathlib import Path

def test_live_env_template_uses_live_placeholders_and_landwolf_domain():
    env = Path(".env.live.example").read_text()
    assert "APP_ENV=production" in env
    assert "STRIPE_SECRET_KEY=sk_live_replace_me" in env
    assert "STRIPE_MONTHLY_PRICE_ID=price_1UF0wdPhxY7l1SSNacgAt3xi" in env
    assert "STRIPE_ANNUAL_PRICE_ID=price_1UF0wcPhxY7l1SSNtwo6diAI" in env
    assert "STRIPE_SUCCESS_URL=https://landwolf.ai/?checkout=success" in env
    assert "STRIPE_CANCEL_URL=https://landwolf.ai/?checkout=cancel" in env

def test_live_webhook_helper_refuses_test_mode_keys():
    script = Path("scripts/register_landwolf_ai_live_webhook.py").read_text()
    assert 'key.startswith("sk_live_")' in script
    assert "https://landwolf.ai/api/billing/webhook" in script
    assert "LandWolf live subscription access" in script

def test_live_docs_do_not_embed_sandbox_price_ids():
    docs = Path("LIVE_STRIPE_DEPLOYMENT.md").read_text() + Path(".env.live.example").read_text()
    assert "price_1UF0dePh6su6RDu3UuTVDEYx" not in docs
    assert "price_1UF0dlPh6su6RDu3ydcc9vDU" not in docs
