# Runtime configuration

The application has four runtime environments: `development`, `test`, `staging`, and `production`.
Configuration is loaded from environment variables. A local `.env` file is supported for development only and is excluded from source control.

## Secret handling

The following values are treated as secrets by the application and are represented with Pydantic `SecretStr` so accidental model/log rendering does not expose their contents:

- `SECRET_KEY`
- `DATABASE_URL`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`

For staging and production, inject these values from the hosting platform's secret manager or encrypted environment-variable facility. Do not bake them into Docker images, commit them to Git, place them in frontend JavaScript, or reuse the same secret across environments.

Generate `SECRET_KEY` with a cryptographically secure generator. For example:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Rotate a compromised key immediately. Rotating `SECRET_KEY` invalidates existing login sessions, which is preferable to continuing with a compromised signing key.

## Startup validation

`Settings` is instantiated while the application imports. In `staging` and `production`, startup fails before traffic is accepted when any required security configuration is missing or unsafe.

Validation requires:

- a unique `SECRET_KEY` of at least 32 characters and not the placeholder value;
- a non-empty `DATABASE_URL`;
- explicit HTTPS `CORS_ORIGINS` with no wildcard;
- `COOKIE_SECURE=true` and `COOKIE_HTTPONLY=true`;
- Stripe API, price, and webhook secrets;
- HTTPS Stripe success and cancel URLs.

This is intentionally fail-closed. A bad deployment should fail rather than silently start with development defaults.

## Browser authentication cookies

Browser authentication uses an `HttpOnly` session cookie. The frontend no longer persists the JWT in `localStorage`, reducing exposure to JavaScript-based token theft.

Recommended production settings:

```env
AUTH_COOKIE_NAME=upi_session
COOKIE_SECURE=true
COOKIE_HTTPONLY=true
COOKIE_SAMESITE=strict
COOKIE_DOMAIN=
COOKIE_PATH=/
```

Leaving `COOKIE_DOMAIN` empty creates a host-only cookie, which is safer unless subdomain sharing is explicitly required. `Secure` ensures the cookie is sent only over HTTPS. `HttpOnly` prevents normal browser JavaScript from reading it. `SameSite=strict` provides strong CSRF resistance for this same-origin web application.

Bearer-token authentication remains supported for API clients through the `Authorization: Bearer ...` header.

If a future frontend is intentionally hosted on a different site and cross-site cookies are required, use `COOKIE_SAMESITE=none` only together with `COOKIE_SECURE=true`, then add a dedicated CSRF token strategy before enabling state-changing cross-site requests.

## CORS

Development may use localhost origins. Staging and production must list exact HTTPS origins as a comma-separated string, for example:

```env
CORS_ORIGINS=https://app.example.com,https://admin.example.com
```

Wildcard CORS is rejected in staging/production because credentials are enabled. Allowed methods are intentionally limited to `GET`, `POST`, and `OPTIONS`, and allowed headers are limited to the headers currently used by the application.

## Staging versus production

Staging should mirror production security behavior while using isolated infrastructure and test billing credentials.

| Setting | Staging | Production |
|---|---|---|
| `APP_ENV` | `staging` | `production` |
| TLS | Required | Required |
| Database | Separate staging DB | Production DB |
| `SECRET_KEY` | Unique staging secret | Unique production secret |
| Stripe | Test-mode key/price/webhook | Live-mode key/price/webhook |
| CORS | Exact staging HTTPS origin(s) | Exact production HTTPS origin(s) |
| Cookies | Secure, HttpOnly, SameSite strict | Secure, HttpOnly, SameSite strict |
| API docs | Enabled | Disabled |
| Schema creation | Migrations only | Migrations only |
| User/data isolation | No production users/data | Production users/data |

Never point staging at the production database, production Stripe account configuration, or production secrets.

Use `.env.staging.example` and `.env.production.example` only as variable manifests. Do not deploy those example values. Populate the real values in the deployment platform's secret/configuration store.

## Deployment examples

### Staging

```env
APP_ENV=staging
CORS_ORIGINS=https://staging.example.com
COOKIE_SECURE=true
COOKIE_HTTPONLY=true
COOKIE_SAMESITE=strict
STRIPE_SUCCESS_URL=https://staging.example.com/?checkout=success
STRIPE_CANCEL_URL=https://staging.example.com/?checkout=cancel
```

Use Stripe test-mode credentials and a staging-only database.

### Production

```env
APP_ENV=production
CORS_ORIGINS=https://app.example.com
COOKIE_SECURE=true
COOKIE_HTTPONLY=true
COOKIE_SAMESITE=strict
STRIPE_SUCCESS_URL=https://app.example.com/?checkout=success
STRIPE_CANCEL_URL=https://app.example.com/?checkout=cancel
```

Use live Stripe credentials, production database credentials, and a production-only signing secret.
