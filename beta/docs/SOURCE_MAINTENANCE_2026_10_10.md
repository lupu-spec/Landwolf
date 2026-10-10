# Production source check — October 10, 2026

Production baseline: v0.12.0, runtime commit
`7b06ded06beca5bb4b54f3dcbaf83158e072c74f`, Render deployment
`dep-db52sd7avr4c73f8u6l0`, live at 12:24:06 UTC. Branch baseline:
`c0c9f728bd4921aa5a8f22cae0ec96b2adda610a`. The live shell independently
reported the same runtime commit. Source state and bounded refresh history were
read before retrying a failed connection.

## Production listing snapshots

| Implemented adapter | State | Retained snapshot records |
| --- | --- | --- |
| Alaska DNR | ready | 170 |
| Arkansas COSL | unavailable | 2 |
| IRS auctions | ready | 1 |
| Michigan DNR | ready | 28 |
| Minnesota DOT | ready | 4 |
| Texas GLO public sales | ready | 29 |
| USDA resales | ready | 19 |
| Treasury real property | ready | 21 |

Seven ready feeds contain 272 raw snapshot records. These counts do not establish
current sale availability, unique properties or complete geographic coverage.
Their production refreshes completed between 12:24 and 12:25 UTC. No healthy
listing feed was manually refreshed or modified.

Only the failed `ar_cosl` provider was retried through the existing live
`Catalog(factory).providers["ar_cosl"].refresh()` implementation. A guard required
its stored status to be `unavailable` before the retry. The official
[COSL catalog](https://cosl.org/Home/Contents) returned HTTP 500 again.
After the retry at 13:58:28 UTC, status remained unavailable, count remained 2,
and last success remained October 9, 04:42:00 UTC. Last-good data was preserved;
no quarantine fingerprint was approved. This is an upstream HTTP failure, not a
confirmed parser change or credential/access rejection.

## Public research adapters

Fresh `ResearchService().lookup(ResearchQuery(...))` calls ran inside the live
service for Dallas (32.7767, -96.7970) and Raleigh (35.7804, -78.6391).
Both reports were ready. Census, FEMA NFHL, USGS elevation and USDA NRCS soils
returned valid results at both points. NC OneMap parcels returned ready in
Raleigh and correctly not-applicable in Dallas. These sample checks do not
establish nationwide coverage or a parcel's legal/environmental condition.

The same two CLI checks in the local check environment returned partial reports
because the FEMA query received HTTP 502 there. Production's successful FEMA
responses supersede that environment-specific result for production status.
No FEMA URL, parser or allowlist was changed to work around it.

## Verification and limitations

| Command/action | Result |
| --- | --- |
| Read live deploy, commit, stored source states and refresh logs | **Passed** |
| Guarded Arkansas-only production retry | **Failed** upstream HTTP 500; snapshot retained |
| `LANDWOLF_DATABASE_URL=sqlite:////tmp/landwolf-mobile-keyboard-sources.db .venv/bin/python -m landwolf.cli sync` | **Failed**, exit 1: Arkansas HTTP 500; seven other adapters ready with the counts above |
| `.venv/bin/python -m landwolf.cli check-research` | **Failed**, exit 1 locally: FEMA HTTP 502; other applicable adapters ready |
| `.venv/bin/python -m landwolf.cli check-research --latitude 35.7804 --longitude -78.6391` | **Failed**, exit 1 locally: FEMA HTTP 502; NC parcels and other applicable adapters ready |
| Live-service Dallas/Raleigh research checks | **Passed**, both ready, all applicable adapters valid |
| Production origin `/api/version`, `/api/health`, anonymous `/api/session` | **Passed**, exact v0.12.0/commit, database health ok, billing/email/trial enabled |
| Source repair regression/release gates and source deployment | **Not run**: no confirmed source code repair was needed |

The external database query tool was blocked by the existing empty IP allowlist.
The existing internal service shell supplied the read-only inspection instead;
network/security permissions were preserved. A direct `landwolf.ai` request from
this check environment returned a non-JSON Site Unavailable page; the Render
production origin returned valid JSON. This environment limitation does not
establish a domain outage. Independent hosted HTTPS checks are recorded with
their actual results in the release verification report.

No source connection recovered during this check: seven listings were already
healthy, all public research adapters worked from production, and Arkansas
remains unavailable. No credential or customer action is required for the
observed blocker. No publisher URL/parser change was confirmed, so no source
code deployment was performed. Stripe, entitlements, grants/pilots, accounts,
source allowlists, retained snapshots and quarantine protections were preserved.
