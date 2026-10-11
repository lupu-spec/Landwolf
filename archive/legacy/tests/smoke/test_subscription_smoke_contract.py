from pathlib import Path

def test_subscription_smoke_contract():
    text = Path("scripts/post_deploy_subscription_smoke.py").read_text().lower()
    required = [
        "api/billing/checkout",
        "api/billing/webhook",
        "stripe-signature",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "subscription_status",
        "active",
        "trialing",
        "canceled",
        "subscription_required",
        "duplicate webhook",
        "expected 402",
    ]
    for token in required:
        assert token in text

def test_subscription_smoke_does_not_print_sensitive_values():
    text = Path("scripts/post_deploy_subscription_smoke.py").read_text().lower()
    for forbidden in [
        "print(password)",
        "print(webhook_secret)",
        "print(auth_cookie)",
        "print(token)",
    ]:
        assert forbidden not in text
