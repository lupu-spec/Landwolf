# Stripe Webhook Persistence and Transactionality Smoke Tests

The deployed application now has a database-backed smoke test:
`scripts/post_deploy_webhook_persistence_smoke.py`.

It validates the durable webhook ledger and entitlement state directly against
the deployment database after sending signed webhook events through the public
webhook endpoint.

## Verified invariants

### Event ID persistence
Every accepted Stripe event is persisted by `stripe_event_id`, protected by a
database unique constraint.

An exact duplicate delivery must leave exactly one ledger row.

### Stripe timestamp persistence
The Stripe event's authoritative `created` timestamp is persisted as
`subscription_events.stripe_created`.

This is distinct from `processed_at`, which records when this application
processed the event.

### Transactional state changes
For a state-changing event, these changes occur in one database transaction:

1. lock the affected user row;
2. evaluate event ordering;
3. update subscription entitlement if the event is authoritative;
4. insert the Stripe event ledger row;
5. commit both together.

If the insert loses a duplicate-event race, the transaction rolls back so no
partial entitlement change survives.

### Duplicate handling
Exact duplicate event IDs return a safe success/no-op. The unique constraint is
the concurrency backstop in case two workers receive the same event at the same
time.

### Older-event protection
Each user stores:

- `last_stripe_event_id`
- `last_stripe_event_type`
- `last_stripe_event_created`

A unique state-changing event whose Stripe `created` timestamp is older than the
last applied event is persisted for audit with:

`processing_result = ignored_stale`

but it cannot overwrite the current subscription state.

## Database migration

Apply:

`database/migrations/002_stripe_webhook_transactional_ordering.sql`

before deploying the application version that uses these fields.

The migration adds the event timestamp/audit columns, user ordering fields, and
supporting indexes.

## Release health order

```text
preflight
  ↓
deploy + migrations
  ↓
core smoke
  ↓
subscription smoke
  ↓
webhook replay/order smoke
  ↓
webhook persistence/transactionality smoke
  ↓
healthy
```

The final persistence smoke requires `DATABASE_URL` in the protected CI
environment because it verifies the database record and user state directly.
That credential must remain an environment secret and is never printed.
