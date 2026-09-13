from pathlib import Path

def test_webhook_replay_smoke_contract():
    text = Path("scripts/post_deploy_webhook_replay_smoke.py").read_text().lower()
    required = [
        "checkout.session.completed",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "duplicate checkout.session.completed",
        "duplicate customer.subscription.updated",
        "duplicate customer.subscription.deleted",
        "out-of-order older active",
        "out-of-order checkout",
        "stripe-signature",
        "created",
        "subscription_status",
    ]
    for token in required:
        assert token in text

def test_replay_smoke_does_not_print_secrets():
    text = Path("scripts/post_deploy_webhook_replay_smoke.py").read_text().lower()
    for forbidden in ["print(webhook_secret)", "print(password)", "print(token)"]:
        assert forbidden not in text
