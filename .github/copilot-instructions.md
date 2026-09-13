# Copilot instructions for Landwolf

## Repository shape

The checked-in repository currently contains the deployable source in
`Landwolf_GitHub_Ready.zip`. When source files are not present in the working
tree, inspect or extract that archive before making assumptions about the
application.

Landwolf is a Python 3.12 FastAPI property-intelligence application:

- `app/` contains the HTTP application, configuration, SQLAlchemy models,
  authentication, search, billing, and the static browser UI.
- `investment_engine/` is a mostly pure-Python/NumPy analysis library for
  distributions, liens, repairs, acquisition costs, Monte Carlo outcomes, and
  bid analysis.
- `scripts/` contains deployment preflight, live smoke checks, Stripe webhook
  registration, and demo-seeding utilities.
- `alembic/` and `database/` contain migration metadata and SQL migrations.
- `tests/` contains API/domain tests plus smoke-test contract tests.

## Build, run, and test commands

Install the pinned development/runtime dependencies:

```bash
pip install -r requirements.txt
```

Run the application locally with a local `.env`:

```bash
uvicorn app.main:app --reload
```

The supported containerized local deployment is:

```bash
cp .env.example .env
docker compose up --build
```

Run the full test suite:

```bash
pytest -q
```

Run one file, one class, or one test:

```bash
pytest -q tests/test_config_security.py
pytest -q tests/test_billing_finalization.py::test_name
pytest -q tests/test_billing_finalization.py::TestClass::test_name
```

The repository does not define a separate lint command or lint workflow.

For a database-backed staging/production environment, use Alembic rather than
`Base.metadata.create_all`:

```bash
DATABASE_URL='postgresql+psycopg://...' alembic upgrade head
```

Before a release, run the fail-closed configuration check:

```bash
python scripts/deployment_preflight.py --environment staging
python scripts/deployment_preflight.py --environment production
```

The live release smoke scripts require a deployed HTTPS URL and the environment
variables documented in the corresponding `POST_DEPLOYMENT_SMOKE.md` and
`STRIPE_*_SMOKE.md` files. The GitHub Actions workflows are the authoritative
CI entry points: `test.yml` runs all pytest tests, while
`release-preflight.yml` runs the preflight unit test and environment checks.

## Architecture and request flow

`app/main.py` constructs the FastAPI application, installs restrictive CORS,
registers the auth/search/billing routers, exposes `/api/health`, and serves
`app/static` at `/`. Settings are instantiated during import, so invalid
staging/production configuration intentionally prevents the process from
starting.

Authentication is implemented in `app/services/auth.py` and
`app/core/security.py`. Registration/login return a JWT for API clients and
also set an HttpOnly cookie for the browser. `current_user` accepts either the
Bearer header or the configured cookie. Email normalization and account-active
checks belong in the auth service, not in route handlers.

SQLAlchemy models in `app/models/entities.py` cover users, canonical property
records, search audit events, and the Stripe webhook ledger. Development/test
startup creates tables automatically; staging/production must use Alembic
migrations. The database session is request-scoped through `get_db`.

Search routes call the shared `app/services/search.py` query builder. The
preview endpoint requires login but returns only aggregate teaser information;
the detailed endpoint requires a Stripe subscription with status `active` or
`trialing` and returns property-level data. Keep this distinction server-side:
the browser must not be treated as an authorization boundary.

Billing checkout maps the public `monthly`/`annual` plan keys to server-side
Stripe Price IDs. `process_webhook` verifies the Stripe signature, persists
every supported event, ignores duplicate event IDs, rejects stale state
transitions, and commits the event ledger plus entitlement update in one
transaction. Changes to webhook behavior must preserve those idempotency,
ordering, and rollback guarantees.

`investment_engine` is separate from the web/API layer. `PropertyModel`
describes an analysis input; `MonteCarloEngine.run` validates it, uses a
seeded NumPy generator, samples configured cost/risk distributions, and
returns percentile-based acquisition cost, profit, loss probability, and ROI
results. Keep simulation inputs explicit and seeded when adding regression
coverage.

The ingestion and provider registry services are extension boundaries, not a
complete provider implementation. New adapters should fetch source records,
normalize them to the canonical property shape, retain source metadata, and
upsert by source parcel identity.

## Repository-specific conventions and invariants

- Treat `app/core/config.py` as a fail-closed security boundary. Staging and
  production require a strong unique `SECRET_KEY`, a database URL, explicit
  HTTPS CORS origins, secure HttpOnly cookies, Stripe secrets/Price IDs, and
  HTTPS checkout URLs. Do not add development fallbacks to production paths.
- Keep secrets in the deployment environment or secret manager. Never commit
  populated `.env` files, Stripe keys/webhook secrets, database credentials, or
  failure-injection secrets.
- Preserve both authentication transports: browser requests use the cookie;
  API clients may use `Authorization: Bearer ...`. Cookie settings are
  environment-controlled and production defaults must remain Secure,
  HttpOnly, and SameSite strict unless the cross-site/CSRF design changes too.
- Subscription access is determined by `PAID_STATUSES` in
  `app/services/quota.py`; do not grant access from
  `checkout.session.completed` alone. Subscription lifecycle events are the
  authority.
- Use Pydantic request/response schemas for API boundaries and SQLAlchemy
  `select` queries in services. Keep route handlers thin and put business
  rules in services.
- Preserve explicit transaction boundaries. In particular, webhook event
  persistence and user entitlement changes must succeed or roll back
  together, and duplicate-event races must remain safe under the unique
  database constraint.
- Keep user-facing detailed search fields behind the subscription gate.
  Preview responses must not expose addresses, parcel IDs, owner information,
  coordinates, exact valuations, or individual opportunity records.
- Use the existing deterministic fixtures and seeded engine behavior for
  investment calculations. Do not silently change distribution semantics,
  percentile meanings, or the maximum iteration guard.
- Release order is intentional: tests, environment preflight, protected
  deployment, core smoke, Stripe subscription smoke, webhook replay/order
  smoke, webhook persistence smoke, and rollback smoke. Do not make deploy
  jobs run independently of preflight.

