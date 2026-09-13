

## Live Stripe deployment for landwolf.ai


### Connected live Stripe objects

- Product: `prod_VFVepZMgPE2lMH` (`LandWolf Pro`)
- Monthly live price: `price_1UF0wdPhxY7l1SSNacgAt3xi` — $29/month
- Annual live price: `price_1UF0wcPhxY7l1SSNtwo6diAI` — $299/year

The live Price IDs are already populated in `.env.live.example`. The deployment host still needs `STRIPE_SECRET_KEY=sk_live_...` and the live `STRIPE_WEBHOOK_SECRET=whsec_...`; those must stay in the hosting provider's secret environment, not source control.


This deployment kit is prepared for **live Stripe payments** at `https://landwolf.ai`.

Use `.env.live.example` as the production environment template. Before deployment, replace the placeholders with values from the live LandWolf Stripe account:

- `STRIPE_SECRET_KEY=sk_live_...`
- `STRIPE_MONTHLY_PRICE_ID=<live $29/month price ID>`
- `STRIPE_ANNUAL_PRICE_ID=<live $299/year price ID>`
- `STRIPE_WEBHOOK_SECRET=<live webhook signing secret>`

Configured production URLs:

- Checkout success: `https://landwolf.ai/?checkout=success`
- Checkout cancel: `https://landwolf.ai/?checkout=cancel`
- Webhook endpoint: `https://landwolf.ai/api/billing/webhook`

After the site is deployed and publicly reachable over HTTPS, register the live webhook with:

`STRIPE_SECRET_KEY=sk_live_... python scripts/register_landwolf_ai_live_webhook.py`

The script intentionally refuses `sk_test_...` credentials.

Important: test-mode products and Price IDs cannot be used for live charges. The live Stripe account must have separate $29/month and $299/year recurring prices, and those live Price IDs must be entered in the deployment environment.

# US Property Intelligence

Deployable real-estate property intelligence web application built around:

- PostgreSQL + PostGIS
- FastAPI
- JWT authentication
- Stripe subscriptions
- Server-side search quota enforcement
- Monte Carlo acquisition analysis
- Provider-ready ingestion architecture
- Docker deployment
- Pytest + Hypothesis + mutation-testing gates

## Product behavior

A registered free user receives **2 lifetime property searches**.

After the second search, the API returns `402 Payment Required` and the UI sends
the user to the subscription checkout. Subscription status is enforced on the
server; hiding a button in the browser does not bypass the limit.

Set the quota with:

```env
```

If a user has an active/trialing Stripe subscription, searches are unlimited
unless a future paid-plan quota is configured.

## Local deployment

```bash
cp .env.example .env
docker compose up --build
```

Open:

```text
http://localhost:8000
```

The application will create its tables on startup in development. For
production, use migrations rather than automatic schema creation.

## Stripe

Create a recurring Stripe Price and set:

```env
STRIPE_SECRET_KEY=...
STRIPE_PRICE_ID=price_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

Configure Stripe webhook:

```text
POST /api/billing/webhook
```

Events handled:

- checkout.session.completed
- customer.subscription.created
- customer.subscription.updated
- customer.subscription.deleted

## Production requirements

Before public launch:

1. Set a strong `SECRET_KEY`.
2. Use managed PostgreSQL/PostGIS.
3. Run behind HTTPS.
4. Configure Stripe webhook signing.
5. Use Alembic migrations.
6. Set trusted CORS origins.
7. Add email verification/password reset.
8. Configure rate limiting/WAF.
9. Add backups and monitoring.
10. Replace sample seed data with provider ingestion.
11. Complete legal/title disclaimers and terms.
12. Run the complete pytest + mutation gate in CI.

## Search semantics

A "search" is a submitted property-search query. Pagination and opening an
individual result do not consume another search. The quota reservation is
transactional to prevent concurrent requests from overspending the free quota.

## Subscription access policy

Only Stripe subscription statuses `active` and `trialing` unlock paid search
access. `past_due`, `canceled`, `unpaid`, and incomplete subscriptions fall
back to the free-plan quota and therefore cannot continue searching once the
no free searches have been consumed.

## Release safety

Run `scripts/deployment_preflight.py` before every staging or production release. See `RELEASE_PREFLIGHT.md`.

## Post-deployment health gate

A release is only considered healthy after `scripts/post_deploy_smoke.py` passes against the live deployment. See `POST_DEPLOYMENT_SMOKE.md`.

## Stripe release verification

Post-deployment validation now includes checkout creation, signed webhook processing, active paid access, webhook idempotency, and revoked-subscription enforcement. See `STRIPE_SMOKE_TESTS.md`.

## Stripe webhook replay safety

Release health now includes duplicate and out-of-order webhook delivery tests for checkout completion, subscription updates, and subscription deletion. See `STRIPE_WEBHOOK_REPLAY_SMOKE.md`.

## Transactional Stripe webhook persistence

Webhook event IDs, Stripe event timestamps, processing outcomes, and authoritative subscription state are persisted transactionally and checked after deployment. See `STRIPE_WEBHOOK_PERSISTENCE_SMOKE.md`.

## Access policy

Property search has no free tier. Users must create an account or log in, then hold an `active` or `trialing` subscription before `/api/search` returns property results. Unauthenticated requests are rejected by authentication; authenticated users without a paid/trialing subscription receive HTTP 402 `SUBSCRIPTION_REQUIRED`.

## Search preview conversion path

There is no free tier for detailed property records. After login, an unsubscribed user can use `/api/search/preview`, which returns only aggregate teaser signals: match count, opportunity strength, top categories, broad acreage range, and broad estimated-value range.

The preview intentionally withholds property addresses, parcel IDs, owner information, coordinates, exact individual valuations, and individual opportunity records. `/api/search` remains subscription-gated with HTTP 402 `SUBSCRIPTION_REQUIRED` until the account is `active` or `trialing`.


## LandWolf Stripe sandbox integration

Stripe-hosted Checkout is wired for:

- Monthly: $29/month (`price_1UF0dePh6su6RDu3UuTVDEYx`)
- Annual: $299/year (`price_1UF0dlPh6su6RDu3ydcc9vDU`), saving $49/year versus monthly billing.

The browser sends only `monthly` or `annual`; the backend maps those plan names to configured Stripe Price IDs, preventing arbitrary client-supplied price IDs.

Webhook URL: `/api/billing/webhook`

Handled events:
`checkout.session.completed`, `customer.subscription.created`,
`customer.subscription.updated`, `customer.subscription.deleted`,
`invoice.payment_failed`, and `invoice.paid`.

Detailed property search is unlocked only when the stored subscription status is `active` or `trialing`.

To register the deployed sandbox webhook after you have a public HTTPS hostname:

`STRIPE_SECRET_KEY=sk_test_... python scripts/register_stripe_webhook.py https://your-landwolf-host`

Store the returned signing secret as `STRIPE_WEBHOOK_SECRET`. Do not commit secret keys or webhook signing secrets.


## Billing completion checklist

The application side of sandbox billing is complete.

Security and entitlement rules:
- Checkout accepts only the server-side plan keys `monthly` and `annual`.
- Stripe Price IDs are selected on the server.
- Webhook signatures are verified before any event is processed.
- Duplicate Stripe event IDs are ignored.
- Older subscription state events cannot overwrite newer state.
- Checkout completion alone does **not** grant paid access.
- `customer.subscription.created` and `customer.subscription.updated` are authoritative for paid access.
- Detailed property results are allowed only for `active` or `trialing`.
- `customer.subscription.deleted` revokes access.
- Webhook event persistence and entitlement updates occur in one database transaction.

Deployment-required values:
- `STRIPE_SECRET_KEY` — LandWolf sandbox `sk_test_...` secret.
- `STRIPE_MONTHLY_PRICE_ID=price_1UF0dePh6su6RDu3UuTVDEYx`
- `STRIPE_ANNUAL_PRICE_ID=price_1UF0dlPh6su6RDu3ydcc9vDU`
- `STRIPE_WEBHOOK_SECRET` — generated when the deployed HTTPS webhook is registered.
- `STRIPE_SUCCESS_URL=https://YOUR_HOST/?checkout=success`
- `STRIPE_CANCEL_URL=https://YOUR_HOST/?checkout=cancel`

The public Stripe webhook target must be:
`https://YOUR_HOST/api/billing/webhook`

Never place Stripe secret keys or webhook signing secrets in source control.


## landwolf.ai billing deployment

Sandbox billing is configured for the LandWolf domain:

- Checkout success: `https://landwolf.ai/?checkout=success`
- Checkout cancel: `https://landwolf.ai/?checkout=cancel`
- Stripe webhook: `https://landwolf.ai/api/billing/webhook`

After the application is deployed and reachable over HTTPS, register the sandbox webhook with:

`STRIPE_SECRET_KEY=sk_test_... python scripts/register_landwolf_ai_webhook.py`

Copy the returned `STRIPE_WEBHOOK_SECRET` into the deployed environment and restart the application.

Do not commit Stripe secret keys or webhook signing secrets.
