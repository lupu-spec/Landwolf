# Post-Deployment Smoke Tests

A deployment is not considered healthy until `scripts/post_deploy_smoke.py`
passes against the live HTTPS endpoint.

## Live checks

The test verifies:

- `/api/health` returns HTTP 200 and reports `ok` or `healthy`;
- the configured CORS origin is allowed exactly and supports credentials;
- a deliberately blocked CORS origin is not reflected as allowed;
- a unique temporary user can register and authenticate;
- login sets an authentication cookie with `HttpOnly`, `Secure`, and `SameSite`;
- the authenticated `/api/auth/me` session resolves to the correct user;
- a new free user starts with zero searches used;
- free searches #1 and #2 succeed and increment usage to 1 and 2;
- free search #3 returns HTTP 402 with `SUBSCRIPTION_REQUIRED`;
- the rejected third search does not increment usage above 2.

Cookie values, passwords, and tokens are never printed.

## CI variables

Configure these per GitHub Environment (`staging` and `production`):

- `SMOKE_BASE_URL` — deployed HTTPS application URL;
- `CORS_PRIMARY_ORIGIN` — the exact browser origin that should be allowed;
- `SMOKE_TEST_EMAIL_DOMAIN` — controlled domain for synthetic smoke accounts,
  if `example.invalid` is not accepted by your registration policy.

The workflow injects a known-blocked test origin automatically.

## Release health chain

```text
configuration preflight
        ↓
      deploy
        ↓
live post-deployment smoke tests
        ↓
   release healthy
```

`.github/workflows/release.yml` expresses this with `needs:` dependencies.
A failed smoke test therefore prevents the `release_healthy` job from running.

## Manual execution

```bash
export SMOKE_BASE_URL="https://staging.example.com"
export SMOKE_ALLOWED_ORIGIN="https://staging.example.com"
export SMOKE_BLOCKED_ORIGIN="https://blocked-smoke-origin.example"
python scripts/post_deploy_smoke.py
```

The test creates one unique account and consumes exactly no free searches.
Use a controlled synthetic-user domain in production and periodically purge
those synthetic accounts according to your retention policy.

Passing startup preflight authorizes deployment; passing this live suite is
what marks the deployed release healthy.

## Paid-path smoke gate

The core smoke suite is followed by `scripts/post_deploy_subscription_smoke.py`, which verifies Stripe checkout creation, signed webhook processing, active subscriber access, and revoked subscriber access. See `STRIPE_SMOKE_TESTS.md`.
