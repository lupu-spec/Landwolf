# Release Preflight and Environment Isolation

The application has a fail-closed preflight that must pass before staging or production release.

## What is checked

The preflight rejects a release when:

- a required environment variable is absent or empty;
- `APP_ENV` does not match the target environment;
- the application secret is too short, low-entropy, or a placeholder;
- a PostgreSQL connection is malformed or contains an obviously weak/default password;
- CORS uses `*`, HTTP, localhost, or another non-HTTPS origin;
- browser cookies are not `Secure` and `HttpOnly`;
- Stripe credentials are missing or malformed;
- production uses a Stripe test secret key;
- staging uses a Stripe live secret key;
- Stripe success/cancel URLs are not HTTPS;
- the free search limit unexpectedly differs from 2;
- JWT expiry is outside the accepted range.

When staging and production configuration files are compared, it also rejects reuse of:

- `SECRET_KEY`;
- `DATABASE_URL`;
- `STRIPE_SECRET_KEY`;
- `STRIPE_WEBHOOK_SECRET`.

It warns by failing when public environment endpoints such as CORS and checkout return URLs are identical, because that usually indicates staging is pointing at production or vice versa.

The validator prints variable names and errors only. It never prints secret values.

## GitHub Environments

Create two GitHub Environments:

- `staging`
- `production`

Store sensitive values as **Environment Secrets**, not repository variables:

- `SECRET_KEY`
- `DATABASE_URL`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`

Store non-secret configuration as Environment Variables:

- `CORS_ORIGINS`
- `JWT_EXPIRE_MINUTES`
- `COOKIE_SECURE`
- `COOKIE_HTTPONLY`
- `COOKIE_SAMESITE`
- `STRIPE_PRICE_ID`
- `STRIPE_SUCCESS_URL`
- `STRIPE_CANCEL_URL`

Do not place production values in `.env` files committed to source control.

For production, configure GitHub Environment protection so the deployment job requires approval and so only the protected release branch can deploy.

## CI

`.github/workflows/release-preflight.yml` performs three checks:

1. unit tests for the preflight rules on every pull request;
2. staging validation using the staging GitHub Environment;
3. production validation using the production GitHub Environment.

Any failure exits non-zero and blocks downstream release jobs.

A deployment workflow should depend on the appropriate preflight job:

```yaml
deploy-production:
  needs: production-preflight
  environment: production
  # deployment steps...
```

This dependency is important. Do not merely run the preflight in parallel with deployment.

## Local / platform preflight

For an environment already injected into the process:

```bash
python scripts/deployment_preflight.py --environment staging
python scripts/deployment_preflight.py --environment production
```

For intentionally local environment files:

```bash
python scripts/deployment_preflight.py \
  --compare-env-files .env.staging .env.production
```

Never commit populated staging or production env files.

`scripts/release.sh` also calls the validator before the platform-specific deployment command:

```bash
scripts/release.sh staging
scripts/release.sh production
```

Place the actual deployment command only after the preflight call so `set -e` prevents release on validation failure.

## Secret generation and rotation

Generate application secrets with a cryptographically secure secret generator. For example:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Use a unique value for every environment.

Never reuse:
- application signing secrets;
- database passwords;
- Stripe webhook signing secrets;
- provider/API secrets.

Rotate a secret immediately if it is committed, logged, copied into a ticket/chat, or otherwise exposed. Updating a secret in a secret manager does not remove it from Git history or old logs.

## Deployment rule

A release is allowed only when all of the following are true:

`tests pass → environment preflight passes → protected environment approval passes → deployment starts`

The preflight is intentionally fail-closed. Unknown, missing, or suspicious configuration stops the release rather than silently falling back to development defaults.

## Post-deployment verification

Passing preflight authorizes deployment; it does not mark the release healthy. The live deployment must then pass `scripts/post_deploy_smoke.py` before the release is considered healthy.
