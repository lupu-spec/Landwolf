from pathlib import Path

def test_live_env_uses_connected_live_price_ids():
    env = Path(".env.live.example").read_text()
    assert "STRIPE_MONTHLY_PRICE_ID=price_1UF0wdPhxY7l1SSNacgAt3xi" in env
    assert "STRIPE_ANNUAL_PRICE_ID=price_1UF0wcPhxY7l1SSNtwo6diAI" in env
    assert "price_live_monthly_replace_me" not in env
    assert "price_live_annual_replace_me" not in env

def test_live_docs_reference_connected_product():
    docs = Path("LIVE_STRIPE_DEPLOYMENT.md").read_text() + Path("README.md").read_text()
    assert "prod_VFVepZMgPE2lMH" in docs
    assert "price_1UF0wdPhxY7l1SSNacgAt3xi" in docs
    assert "price_1UF0wcPhxY7l1SSNtwo6diAI" in docs
