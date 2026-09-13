# Stripe Webhook Replay and Ordering Smoke Tests

`scripts/post_deploy_webhook_replay_smoke.py` validates that the deployed billing
webhook behaves safely when Stripe retries events or delivers them out of order.

## Events covered

The smoke test sends correctly signed synthetic versions of:

- `checkout.session.completed`
- `customer.subscription.updated`
- `customer.subscription.deleted`

## Idempotency checks

Each event is delivered once, then replayed with the exact same Stripe event ID.

Expected behavior:

- the endpoint returns success for the duplicate;
- the duplicate is a no-op or otherwise safe;
- account state does not change incorrectly;
- no duplicate entitlement is created;
- no canceled subscription is reactivated.

The application should persist Stripe event IDs so exact duplicate deliveries can
be recognized.

## State-transition checks

The sequence tested is:

```text
checkout.session.completed
        ↓
customer.subscription.updated (active)
        ↓
customer.subscription.deleted (canceled)
```

The smoke test verifies that the user is active after the update and no longer
active after deletion.

## Out-of-order checks

After cancellation, the test deliberately sends older events with unique event
IDs but earlier Stripe `created` timestamps:

1. an older `customer.subscription.updated` event with `status=active`;
2. an older `checkout.session.completed` event.

Neither older event may resurrect paid access.

This means webhook handling should track the last authoritative Stripe event time
(or an equivalent monotonic version/state marker) for the subscription/customer
and ignore state-changing events that are older than the state already applied.

## Recommended persistence

For each Stripe event, persist at minimum:

- Stripe event ID;
- event type;
- Stripe `created` timestamp;
- customer ID;
- subscription ID;
- processed timestamp;
- processing result.

For subscription state, persist at minimum:

- subscription ID;
- current status;
- last Stripe event ID;
- last Stripe event type;
- last Stripe event `created` timestamp.

The update should occur transactionally so duplicate and out-of-order events
cannot race each other into an invalid entitlement state.

## Release health chain

```text
configuration preflight
        ↓
deploy
        ↓
core smoke
        ↓
subscription smoke
        ↓
webhook replay/order smoke
        ↓
release healthy
```

A release fails health verification if duplicate or stale webhook delivery can
change entitlement incorrectly.

## Persistence-level verification

Replay/order behavior is followed by a database-backed smoke test that verifies event IDs, Stripe timestamps, and processing outcomes were actually persisted transactionally. See `STRIPE_WEBHOOK_PERSISTENCE_SMOKE.md`.
