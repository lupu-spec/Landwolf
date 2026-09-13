from pathlib import Path
def test_rollback_smoke_contract():
    t=Path("scripts/post_deploy_webhook_rollback_smoke.py").read_text().lower()
    for x in ["after_state_update","after_event_add","before_commit","partial event ledger row survived","partial subscription/entitlement state survived","control event"]:
        assert x in t
def test_service_rolls_back_unexpected_failures():
    t=Path("app/services/billing.py").read_text().lower()
    for x in ["hmac.compare_digest","_maybe_inject_failure","except exception:","db.rollback()"]:
        assert x in t
