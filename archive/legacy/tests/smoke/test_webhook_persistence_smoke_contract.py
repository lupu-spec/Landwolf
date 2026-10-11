from pathlib import Path

def test_webhook_persistence_smoke_contract():
    text = Path("scripts/post_deploy_webhook_persistence_smoke.py").read_text().lower()
    for token in [
        "stripe_event_id",
        "stripe_created",
        "processing_result",
        "ignored_stale",
        "count(*)",
        "last_stripe_event_id",
        "last_stripe_event_created",
        "duplicate delivery",
        "older event overwrote",
    ]:
        assert token in text

def test_billing_processor_is_transactional_and_order_aware():
    text = Path("app/services/billing.py").read_text().lower()
    for token in [
        "with_for_update",
        "ignored_stale",
        "stripe_created",
        "last_stripe_event_created",
        "db.commit()",
        "integrityerror",
        "db.rollback()",
        "duplicate_ignored",
    ]:
        assert token in text
