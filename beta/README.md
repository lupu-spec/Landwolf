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

## Source coverage

Search accepts all 50 US states, or `US` for the nationwide view. The live adapters
read these official inventories:

| Source | Records supplied |
| --- | --- |
| Arkansas Commissioner of State Lands | Upcoming county tax-delinquent land auctions |
| Texas General Land Office | Public land-sale tracts |
| USDA RD / FSA | Federal foreclosure and REO listings across the 50 states |
| U.S. Treasury | Federal forfeited real-estate auctions across the 50 states |
| IRS | Federal tax-seizure real estate auctions across the 50 states |
| Alaska DNR | State land auctions and direct-sale inventory |
| Michigan DNR | General-public BuyNow parcels marked available |

This is **partial inventory coverage**, not every listing in every state or county.
A federal program may have no current records in a state. HUD and GSA are directory
links only. Nationwide pre-foreclosure and tax-lien certificate feeds are not
connected. The authenticated Data coverage page distinguishes feed snapshots,
directory links, current record counts, and gaps for every state and sale category.
See [SOURCES.md](docs/SOURCES.md) for the original sources and parsing rules.

Each provider replaces only its own inventory after a complete successful retrieval.
A failure preserves that provider's last snapshot and displays its status. At most
two providers refresh concurrently; new adapters allow 240 requests per refresh
including one bounded retry for transient failures, 30-second request timeouts,
an 8 MB response limit and a 300-second overall deadline. The original GLO adapter
keeps its stricter 180-second deadline. Inventories are bounded, URLs are explicitly
allowlisted, and redirects are rejected. Refreshes run every six hours.

Search uses database filtering, counting and pagination. Unknown price and acreage
remain null, sort last, and do not pass an applicable numeric filter. Minimum bids,
government bids, tax balances and source appraisals remain distinct. Past auction
dates and bid deadlines are excluded from current search even between refreshes.
Ambiguous published dates are withheld for review. Saved entries remain accessible
with their inactive or expired status. Times and cancellations must still be
confirmed at the original source before acting.

Map points appear only when a source supplies validated coordinates. New inventories
without parcel coordinates remain in the list and have no invented map marker.
No owner contact lists or interested-party columns are imported. Title, ownership,
liens, flood risk and current market values are not independently verified.

## Free public property research

After signing in, open **Property research** and enter a complete street address
or coordinates. Census geographic lookup, FEMA digital flood mapping, USGS ground
elevation and USDA NRCS soils are connected without API keys. North Carolina OneMap
adds county parcel identifiers, GIS acreage and reported assessment values in NC.
Each card shows coverage, uncertainty, retrieval time and available source dates.
No MLS, paid provider account or usage-based API subscription is enabled.

An address result is an interpolated Census point; it may fall on a road or
neighboring parcel. It never becomes a listing map marker. Reference values do not
prefill the deal model. A property's **Research this location** button uses its
published point, or asks for an address/verified point if none is available.
Failures are independent and missing flood data stays unknown. Reports are held in
a bounded memory cache for up to six hours, not saved to accounts or the database.
See [FREE_DATA.md](docs/FREE_DATA.md) for API contracts, limitations and MLS access.

Run actual public API checks explicitly (not part of deterministic fixture CI):

```sh
.venv/bin/python -m landwolf.cli check-research
.venv/bin/python -m landwolf.cli check-research --latitude 35.7804 --longitude -78.6391
```

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
come from Texas GLO and Alaska DNR. Interactive basemaps use OpenStreetMap contributors with visible
attribution and normal browser caching; no offline tile harvesting is implemented.
