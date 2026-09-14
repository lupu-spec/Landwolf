# LandWolf free beta

A separate rebuild of LandWolf with the original wordmark, wolf logo, white/navy
palette, and rural photography. Fresh email/password accounts unlock source-backed
property search, map/list browsing, saved properties, and reproducible deal analysis.
All beta features are free. This application contains no checkout or Stripe gate.

## Run locally

Prerequisites: Python 3.12+, Node 24, and uv. From this directory:

```sh
uv sync --frozen --dev
npm ci
npm run build
.venv/bin/python -m landwolf.cli init-db
.venv/bin/python -m landwolf.cli sync
.venv/bin/uvicorn landwolf.main:create_app --factory --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` and create a new account. The local SQLite database is
ignored by Git. The source refreshes every six hours while the process runs.
The public health endpoint is `/api/health`. API documentation is disabled.
The application wheel includes the built browser assets.

## What is live

The initial connector reads the [Texas General Land Office public land-sale
inventory](https://www.glo.texas.gov/veterans/land-sale/public). It retrieves a complete
inventory before replacing active records, then enriches each tract from its official
detail page. Every result has a source link, retrieval time, published price, acreage,
county, and explicit unknowns. Map markers use coordinates published by the source.
They are location points, not surveyed parcel boundaries. Source outages preserve
the last complete inventory and display an availability warning. Detail freshness
is tracked separately from inventory freshness.

Coverage is currently this Texas inventory only. County tax sales, foreclosures,
municipal surplus, other states, verified ownership/liens/flood overlays, comparable
sales, and independent valuations are **not connected**. Searches outside coverage
show that limitation. An upstream listing does not establish continued availability.
The background connector performs at most 500 sequential detail requests, with a
180-second overall refresh deadline, 15-second request timeouts, response size limits,
and an allowlist of official source URLs. An unexpected or empty source table requires
manual review; it cannot erase the prior inventory.

## Deal model

Investors explicitly enter resale and repair ranges, title/closing costs, a lien and
back-tax reserve, holding costs, buyer premium, selling costs, and financing. A seeded
10,000-scenario triangular model reports net-profit percentiles, median ROI, loss
probability with a sampling interval, and a scenario score. It does not infer market
value from the seller's asking price or treat missing costs as zero.

Maximum bid is the largest cent-rounded bid satisfying the entered sampled loss
limit, minimum median profit, and median ROI. The search reuses the same draws for
every bid. No feasible bid is represented distinctly from zero. Model version and
seed are displayed. See [MODEL.md](docs/MODEL.md) for equations and limitations.

## Security and operation

- Argon2id password hashes; revocable opaque sessions stored as hashes; HttpOnly,
  SameSite=Strict cookies; Secure cookies and HSTS on HTTPS.
- Server-side account ownership, idle/absolute expiry, origin checks, CSRF tokens,
  same-origin APIs, body limits, shared database rate limits, and restrictive CSP.
- Secrets and personal records never belong in Git or log messages. Source HTML is
  parsed into validated fields; the browser uses text nodes and allowlisted URLs.
- Accounts have no roles or billing privileges. Email ownership verification and
  automated password recovery are not implemented; plan these before broad public
  enrollment. No transactional email is sent by this beta.
- Use one application instance/worker for the initial source scheduler. A future
  multi-instance rollout requires a distributed scheduler lease. Configure trusted
  proxy addresses deliberately; never trust arbitrary client forwarding headers.

Schema version 1 uses `lw2_` tables. `init-db` bootstraps only this initial schema;
future changes need reviewed migrations. Production requires a separate PostgreSQL
database and a validated HTTPS origin; it does not auto-create tables during request
startup. On Render, the default is the service's platform-assigned
[`RENDER_EXTERNAL_URL`](https://render.com/docs/environment-variables), available
before startup. A missing or invalid Render URL stops startup. Set
`LANDWOLF_PUBLIC_ORIGIN` explicitly for an attached custom domain or another host;
this override takes precedence and must also pass validation. Request headers never
select the trusted origin. Configure backups/retention before public enrollment.

## Deployment and verification

[render.beta.yaml](../render.beta.yaml) defines a new Render service and database.
It has automatic deployment disabled and does not modify the existing service.
Provisioning the specified hosting plans may incur charges; this file is a reviewable
configuration, not evidence that anything is deployed. Select branch
`codex/landwolf-beta-rebuild` and Blueprint path `render.beta.yaml`. No placeholder
origin is needed: Render supplies the service address, and the pre-deploy command
bootstraps the fresh database. Deploy, then verify the actual assigned HTTPS origin,
new-account login, API health, live sync, save ownership, cookies, and browser flow.

The commands and no-false-verification rule are in [AGENTS.md](AGENTS.md).
See [VERIFICATION.md](docs/VERIFICATION.md) for observed results and outstanding gates.
Fixture tests are isolated from runtime inventory and live checks.

Original branding was supplied by the owner. Land photography and listing facts
come from Texas GLO. Interactive basemaps use OpenStreetMap contributors with visible
attribution and normal browser caching; no offline tile harvesting is implemented.
