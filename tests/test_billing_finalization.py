from pathlib import Path

def test_checkout_completion_does_not_directly_grant_entitlement():
    billing = Path("app/services/billing.py").read_text()
    assert 'if event_type == "checkout.session.completed":' in billing
    assert "return None" in billing
    assert 'event_type in {"customer.subscription.created", "customer.subscription.updated"}' in billing

def test_checkout_return_ui_waits_for_webhook_state():
    js = Path("app/static/app.js").read_text()
    assert 'params.get("checkout")' in js
    assert "Activating your LandWolf subscription" in js
    assert "setTimeout(refresh, 1500)" in js
    assert "Checkout was canceled" in js
