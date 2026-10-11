
# Deployment checklist

## Infrastructure

- [ ] Managed PostgreSQL 16 + PostGIS 3.4
- [ ] HTTPS reverse proxy/load balancer
- [ ] Secret manager
- [ ] Object storage for raw source archives
- [ ] Scheduled ingestion worker
- [ ] Monitoring/logging
- [ ] Database backups + restore test

## Application

- [ ] Alembic migration pipeline
- [ ] Production CORS
- [ ] Password reset/email verification
- [ ] Login abuse/rate limiting
- [ ] CSRF strategy for cookie-based auth if auth is moved to cookies
- [ ] Content security policy
- [ ] Audit logging
- [ ] Stripe webhook configured and tested
- [ ] Stripe subscription cancellation handling
- [ ] Terms/privacy/disclaimer pages

## Data

- [ ] Texas TxGIO parcel adapter
- [ ] Collin/Denton/Dallas/Grayson/Fannin county adapters
- [ ] FEMA NFHL enrichment
- [ ] USGS TNM enrichment
- [ ] Census enrichment
- [ ] OSM enrichment
- [ ] Foreclosure adapters
- [ ] Government disposition adapters
- [ ] Historical snapshots
- [ ] Source confidence/freshness scoring

## Search

- [ ] PostGIS spatial filters
- [ ] Saved searches
- [ ] Search result pagination
- [ ] Property detail page
- [ ] Map view
- [ ] Search audit events
- [ ] Quota analytics

## Acquisition intelligence

- [ ] Monte Carlo API endpoint
- [ ] Maximum rational bid
- [ ] P10/P25/P50/P75/P90 valuation
- [ ] TAC breakdown
- [ ] lien survival model
- [ ] repair uncertainty
- [ ] hard-stop decision engine
- [ ] opportunity score
- [ ] downloadable property report

## Environment security

- [x] Fail-fast validation for required staging/production variables
- [x] Secret values wrapped with `SecretStr`
- [x] `.env` files excluded from source control
- [x] Exact HTTPS CORS required outside development/test
- [x] Browser JWT moved from `localStorage` to an HttpOnly cookie
- [x] Secure/HttpOnly/SameSite cookie policy configurable by environment
- [x] Production interactive API docs disabled
- [x] Staging and production example manifests documented
- [ ] Store deployment secrets in the cloud/provider secret manager
- [ ] Rotate secrets on a defined schedule and after any suspected exposure
- [ ] Terminate TLS at the trusted load balancer/reverse proxy and enforce HTTPS redirects there

See `CONFIGURATION.md` for the full staging-versus-production configuration policy.

## Mandatory release preflight

Every staging and production deployment must depend on the release preflight. See `RELEASE_PREFLIGHT.md` and `.github/workflows/release-preflight.yml`.

## Post-deployment smoke gate

After deployment, run `scripts/post_deploy_smoke.py` against the live URL. The release must not be marked healthy unless health, CORS, authentication, secure-cookie, and two-search quota checks all pass. See `POST_DEPLOYMENT_SMOKE.md`.

## Subscription release gate

After the core smoke suite passes, run `scripts/post_deploy_subscription_smoke.py`. A release is not healthy until checkout creation, subscription activation, paid search access, webhook idempotency, and revoked-access enforcement all pass.

## Stripe webhook replay/order gate

After subscription smoke tests, run `scripts/post_deploy_webhook_replay_smoke.py`. A release must fail if duplicate or stale Stripe events can corrupt or resurrect subscription access.

## Webhook persistence migration and smoke gate

Apply `database/migrations/002_stripe_webhook_transactional_ordering.sql` before release. The deployment is not healthy until `scripts/post_deploy_webhook_persistence_smoke.py` verifies event-ledger persistence, duplicate suppression, atomic state transitions, and stale-event protection.
