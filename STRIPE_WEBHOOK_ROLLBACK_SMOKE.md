# Stripe Webhook Transaction Rollback Smoke Tests

The live rollback smoke test forces controlled failures at `after_state_update`, `after_event_add`, and `before_commit`.

Each injected failure must return 5xx, leave zero rows for the failed Stripe event ID, and leave subscription/entitlement state unchanged. A final non-injected control event must then commit normally.

Failure injection is disabled unless `WEBHOOK_FAILURE_INJECTION_SECRET` is configured. Keep it only in protected CI/deployment secrets. If production policy forbids deliberate fault injection, run this gate in production-equivalent staging and leave the production secret unset.
