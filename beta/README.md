# LandWolf free application

A separate rebuild of LandWolf with the original wordmark, wolf logo, white/navy
palette, and rural photography. Fresh email/password accounts unlock source-backed
property search, map/list browsing, saved properties, and reproducible deal analysis.
All features are free. This application contains no checkout or Stripe gate.

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
prefill a valuation. **Research property** restores your saved research location,
or uses a published point or full street-shaped source-address field for review.
Address handoff is available across the connected feeds, not limited to IRS/USDA.
Otherwise it asks for an address
or verified point; it never geocodes a tract or county as a parcel.
Failures are independent and missing flood data stays unknown. Reports are held in
a bounded memory cache for up to six hours, not saved to accounts or the database.
See [FREE_DATA.md](docs/FREE_DATA.md) for API contracts, limitations and MLS access.

Run actual public API checks explicitly (not part of deterministic fixture CI):

```sh
.venv/bin/python -m landwolf.cli check-research
.venv/bin/python -m landwolf.cli check-research --latitude 35.7804 --longitude -78.6391
```

## Deal model

Resale starts at 95% / 100% / 120% of the published price or entered bid, labeled
as a hypothetical scenario, not market value. Percentages and dollar inputs are
editable; explicit resale overrides are preserved until the user reapplies the range.
Unestimated repair ranges, title/closing costs, lien reserves, holding costs/period,
buyer premiums, selling costs and financing default to zero by owner request.
Zero placeholders require a warning acknowledgment in the UI and trigger warnings
in API results; they are not verified zero costs or statistical estimates. A seeded
10,000-scenario triangular model reports net-profit percentiles, median ROI, loss
probability with a sampling interval, and a scenario score. It does not infer market
value from the seller's asking price. The current feeds lack calibrated local or
broader-area cost estimates; no ChatGPT-generated figures are presented as evidence.

**Save property / Saved ✓** is beside the card actions and in the sticky detail bar.
**Saved properties** lists all account-owned saves, including manually entered
properties, most recently updated first, with pagination and no inherited Explore
filters. **Add a property** opens Research; enter an address or coordinate pair and
select **Save property**. No matching source listing or successful upstream lookup
is required. Saved manual properties are private research records, not published
listings or confirmed sales. **Save changes** retains a name and selected address
or coordinates across reloads, sign-outs and devices. A stale revision returns 409
and asks the user to reopen the record rather than overwrite newer edits.
Address-only handoffs always wait for the user to select **Research location**.
The Research navigation also carries the most recently opened property.
Missing locations remain missing until the user supplies one; user locations never
overwrite source coordinates or become official map markers. A repeated bookmark
does not overwrite a saved location. Saving does not persist scenarios or reports.
Scenario drafts are kept in bounded page-session memory (up to 50 properties), cleared
on reload/sign-out. **Research property** retains the property context and offers
**Open deal scenario**. **Find similar properties** prefills state, county, sale
category and minimum acreage (rounded down to 0.01 acre), clearing old price/source
filters. It searches equal-or-larger acreage, not a statistically matched cohort.

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
  automated password recovery are not implemented. No transactional email is sent.
- Use one application instance/worker for the initial source scheduler. A future
  multi-instance rollout requires a distributed scheduler lease. Configure trusted
  proxy addresses deliberately; never trust arbitrary client forwarding headers.

Schema version 2 uses `lw2_` tables. `init-db` bootstraps v2 or runs the additive,
transactional v1 → v2 migration. It adds `lw2_saved_records`, copies existing account
bookmarks and creation times, and retains the old bookmark table, accounts, sessions
and source listings. Repeated runs are idempotent; unknown versions fail before DDL.
Migration calls are serialized with a PostgreSQL transaction advisory lock or SQLite
immediate transaction. No dependency, database instance or plan change is needed.
The predeploy command runs the migration before serving the new image. V1 images
require schema 1 and are not a direct rollback after migration: use a v2-compatible
fix-forward release, preserving the new records. There may be a brief health-check
transition during the initial v1 → v2 cutover. Production requires a separate PostgreSQL
database and a validated HTTPS origin; it does not auto-create tables during request
startup. On Render, the default is the service's platform-assigned
[`RENDER_EXTERNAL_URL`](https://render.com/docs/environment-variables), available
before startup. A missing or invalid Render URL stops startup. Set
`LANDWOLF_PUBLIC_ORIGIN` explicitly for an attached custom domain or another host;
this override takes precedence and must also pass validation. Optional
`LANDWOLF_ADDITIONAL_ORIGINS` is a JSON array of at most four explicit origins.
Every write must match both a configured origin and that request's Host; one allowed
domain cannot write to another. Cookies are host-only, Secure and SameSite=Strict.
Request headers never select the trusted origins. Backup restoration remains an
outstanding operational check.

## Deployment and verification

[render.beta.yaml](../render.beta.yaml) describes the existing rebuilt Render service
and PostgreSQL database, promoted to free production without replacing their data.
Resource names retain `beta` for continuity; automatic deployment stays disabled.
The deploy branch is `codex/landwolf-beta-rebuild`, with Blueprint path
`render.beta.yaml`. The legacy service/main branch remains a rollback reference.
Do not merge legacy configuration into the new service or create duplicate resources.

The canonical origin is `https://landwolf.ai`; Render redirects `www.landwolf.ai`
to the apex and provisions HTTPS. The existing `landwolf-free-beta.onrender.com`
address remains available. Set the three explicit origins as shown in the Blueprint
before moving domain bindings. Apex DNS uses Render's `216.24.57.1` A record;
`www` uses a CNAME to `landwolf-free-beta.onrender.com`. Preserve mail and unrelated
DNS records. Verify authoritative/public DNS, HTTPS redirects, health, sign-in,
save persistence and disabled payments after cutover. The Blueprint describes the
desired configuration; observed deployment/DNS results are recorded below.

The commands and no-false-verification rule are in [AGENTS.md](AGENTS.md).
See [VERIFICATION.md](docs/VERIFICATION.md) for observed results and outstanding gates.
Fixture tests are isolated from runtime inventory and live checks.

Original branding was supplied by the owner. Land photography and listing facts
come from Texas GLO and Alaska DNR. Interactive basemaps use OpenStreetMap contributors with visible
attribution and normal browser caching; no offline tile harvesting is implemented.
