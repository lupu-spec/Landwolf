# Stripe Subscription Post-Deployment Smoke Tests

`scripts/post_deploy_subscription_smoke.py` validates the paid-access path against
the deployed application after the core smoke suite passes.

## What it verifies

1. A unique synthetic user can register and log in.
2. The account consumes its no free searches.
3. Search #3 is blocked with HTTP 402 before subscription.
4. `POST /api/billing/checkout` creates an HTTPS Stripe checkout URL.
5. A Stripe-signed `customer.subscription.updated` event with `status=active`
   is accepted by the webhook endpoint.
6. Re-delivering the exact same event is accepted without duplicating the
   subscription transition, validating webhook idempotency.
7. `/api/auth/me` reports `active` or `trialing`.
8. The already-quota-exhausted account can search while paid.
9. A Stripe-signed `customer.subscription.deleted` event revokes paid status.
10. `/api/auth/me` no longer reports an active paid subscription.
11. A subsequent search is immediately blocked again with HTTP 402 and
    `SUBSCRIPTION_REQUIRED`.

## Required CI configuration

The GitHub Environment used for smoke testing must provide:

### Variables
- `SMOKE_BASE_URL`
- `CORS_PRIMARY_ORIGIN`
- `SMOKE_TEST_EMAIL_DOMAIN`
- `STRIPE_PRICE_ID`

### Secrets
- `STRIPE_WEBHOOK_SECRET`

The webhook secret is injected only into the CI runner. The smoke test never
prints it.

## Important Stripe behavior

The smoke test does **not** complete a real credit-card Checkout transaction.
Instead it verifies that the deployed app can create the real checkout session,
then exercises the webhook state transition using correctly signed synthetic
Stripe events.

That provides deterministic release verification without charging a card or
creating a live financial transaction.

For staging, use Stripe test-mode credentials and a test-mode Price.

For production, checkout creation uses the production Stripe configuration, but
the synthetic signed webhook changes only the dedicated synthetic smoke-test
user. Use a controlled smoke-test email domain and clean these accounts
periodically.

## Webhook safety

Synthetic events use unique event IDs and subscription IDs and include
`metadata.smoke_test=true`.

The application should keep webhook handling idempotent by persisting Stripe
event IDs. A duplicate event must be a no-op or otherwise safe success.

## Release health chain

```text
configuration preflight
        ↓
      deploy
        ↓
 core smoke tests
        ↓
 Stripe subscription smoke tests
        ↓
   release healthy
```

A release must not be marked healthy if the paid path fails even when the core
application is otherwise reachable.

## Replay and ordering

The subscription smoke gate is followed by `scripts/post_deploy_webhook_replay_smoke.py`, which verifies exact duplicate delivery and stale/out-of-order webhook safety. See `STRIPE_WEBHOOK_REPLAY_SMOKE.md`.
