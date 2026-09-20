# Premium beta framework

This branch implements priority one and defines typed extension contracts for the
remaining priorities. It preserves the wolf logo, navy/white theme, authenticated
search and free access. Saved properties remain permanently removed.

| Priority | This beta | Gate before activation or expansion |
| --- | --- | --- |
| 1. Trust and usability | County-scoped publisher parcel identities; distinct sale events; field evidence; refresh history and quarantine; state/county coverage; concise research summary; responsive navigation; one-use email verification/recovery; additive schema v4 | All repository gates; hosted HTTPS check; configured verified email sender; staging restore rehearsal before promotion |
| 2. Decision quality | `ValuationRequest`, `ValuationResult`, `ValuationProvider`; supported results require comparables, evidence and a range | Licensed or reusable comparable-sale evidence, calibration/backtesting, parcel geometry, cost evidence, explainable assumptions and export review |
| 3. Partner pilot | `PartnerConsent`, `PartnerGateway`; named recipients, selected fields, disclosure version and explicit consent | Approved partners and disclosure text; consent receipt/storage and revocation policy; delivery safeguards; sponsored-placement labeling; separate commercial/privacy review |
| 4. Expansion | `SourceReadiness`; parser, live-check, reuse-review and monitoring gates | Review and connect each adapter explicitly; report partial coverage; establish freshness targets and incident ownership |

The authenticated `/api/capabilities` endpoint and Data coverage page distinguish
beta functionality from framework-only work. Priorities two through four do not
provide working valuation services, partner advertising, lead sharing or automated
source onboarding. These are extension interfaces, not additional active APIs.

## Evidence and identity

A parcel identity requires a publisher parcel number, state and county. Tract
numbers, street text, points and county centroids never establish a match. Exact
county-scoped matches can link separate sale events; unresolved records remain
separate. This is conservative entity linking, not nationwide deduplication or
boundary verification. Arkansas now retains its explicit published parcel ID.

Property details distinguish reported, calculated and unknown facts, retrieval time
and publisher date. Research summaries are deterministic descriptions of available
evidence; they generate no unsupported market values or risk probabilities. Missing
FEMA results remain unknown. Point research cannot clear a whole parcel.

Source history retains the latest 40 runs per provider (five displayed). A complete
bounded snapshot is published atomically. Losing all of at least two unexpired
records, losing over half of at least ten, or changing three prices by more than
50% quarantines the candidate. Last-good data stays visible with a warning.
Inactive sale-event history expires after 365 days. Operator review commands:

```sh
.venv/bin/python -m landwolf.cli review-source --source mn_dot
# Review the original publisher inventory, count change and exact candidate hash.
# Approval expires after 24 hours and authorizes only that candidate snapshot.
.venv/bin/python -m landwolf.cli approve-source --source mn_dot --fingerprint REVIEWED_SHA256
.venv/bin/python -m landwolf.cli sync
```

Do not approve an unexplained anomaly just to make a health indicator green.
County coverage means observed records, not complete jurisdiction coverage.

## Account email

The default is `LANDWOLF_MAIL_PROVIDER=disabled`; the UI states that delivery is
unavailable. To enable it, configure a verified sender in Resend and add these
variables securely to the isolated staging service:

```text
LANDWOLF_MAIL_PROVIDER=resend
LANDWOLF_MAIL_FROM=<verified sender address>
LANDWOLF_MAIL_API_KEY=<secret supplied through Render>
```

Never place a credential in Git, a screenshot or a chat message. Email links expire
in 30 minutes, are single-use, and hold the token in a URL fragment removed at page
startup. The database stores a hash. Reset revokes every account session. Requests
are rate-limited and return the same message for known and unknown accounts.
Failed delivery invalidates the issued token. Verification currently labels the
account; sign-in remains the search gate and existing accounts are not locked out.

## Isolated staging and recovery

Deployed on 2026-09-20 with the owner's approval of the added $6.30/month database
charge: [staging beta](https://landwolf-premium-staging.onrender.com/).
The active Blueprint is `render.staging.paid.yaml` on
`codex/landwolf-premium-staging`. It uses a free web service and separate PostgreSQL
18 `0.1c-256mb` instance with 1 GB storage. External database access and storage
autoscaling are disabled. This paid database has no free-database 30-day expiry.
The approved estimate is before tax and usage overages. Existing production
services, databases, domains and accounts were not modified.

`render.staging.yaml` is an unused free-database alternative. Render allows only
one active free database per workspace, and `landwolf-db` occupies that slot.
Never apply both staging Blueprints or repurpose an existing database.

The service's automatic deploys are off. Blueprint Auto Sync remains enabled:
editing the linked Blueprint can still apply infrastructure changes. Automatic
approval review rejected disabling that setting as outside the deployment approval.
Do not edit infrastructure or pricing without the owner's applicable authorization.
The staging startup script explicitly checks its environment, runs the migration,
and starts the server only after migration succeeds. Production startup is unchanged.

Email remains disabled until a verified sender/provider credential is configured.
Render supplies the service's HTTPS origin. Responses use `noindex, nofollow`;
the website is public, with authenticated research/search. Staging accounts are
separate from production. The free web service can sleep, so its in-process
six-hour source refresh does not run while asleep. See
[Render's free-resource limits](https://render.com/docs/free).

Schema v4 adds trust/recovery tables while preserving accounts and existing
listings. It never recreates Saved tables. CI rehearses `pg_dump` and `pg_restore`
against a disposable PostgreSQL service and compares every table's row digest.
That test does not prove a production backup exists or has been restored.
Before promotion, configure a backup/retention destination and restore a staging
snapshot into another isolated database, then verify sign-in and evidence queries.

`scripts/check_hosted_staging.py` tests only the fixed staging URL and refuses a
non-staging environment or enabled outbound email. Its dedicated GitHub workflow
runs when that script/workflow changes on the staging branch. It creates one
disposable account per run and checks live API and Chromium/WebKit journeys at
390px/1440px, retaining screenshots for seven days without credentials or traces.
Real email delivery and an isolated restore of a staging snapshot remain separate
promotion gates. Evidence and unresolved checks belong in `VERIFICATION.md`.
