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

Provisioning update, 2026-09-20: the owner approved the free staging proposal, but
Render reports an existing free `landwolf-db` in this workspace. Render permits
only one active free PostgreSQL instance per workspace, so the approved proposal
cannot add another free database. Existing databases must not be deleted or reused.
`render.staging.paid.yaml` is a reviewable alternative awaiting separate approval
of the added charge: free web service plus PostgreSQL `0.1c-256mb`, 1 GB storage,
approximately $6.30/month before tax and usage overages at the observed
[Render pricing](https://render.com/pricing). Storage autoscaling is disabled.
Apply only one staging Blueprint. The paid alternative has no free-database
30-day expiry; its backup and restore still require hosted verification.
Neither staging Blueprint has been provisioned. Docker Blueprint application also
requires a fresh authenticated Render Dashboard session in the cloud browser.

Use root `render.staging.yaml` from `codex/landwolf-premium-staging`, after reviewing
the proposed resources. It creates a separate web service and PostgreSQL database,
does not attach production domains, disables auto-deploy, and disables email until
configured. Render supplies the service's HTTPS origin. The staging response is
marked `noindex, nofollow`; it is not a private-network environment.

The free web service can sleep; its in-process six-hour refresh does not run while
asleep. The free PostgreSQL database expires after 30 days and has no managed
backups. This configuration is temporary review infrastructure, not durable
production infrastructure. See [Render's free-resource limits](https://render.com/docs/free).

Schema v4 adds trust/recovery tables while preserving accounts and existing
listings. It never recreates Saved tables. CI rehearses `pg_dump` and `pg_restore`
against a disposable PostgreSQL service and compares every table's row digest.
That test does not prove a production backup exists or has been restored.
Before promotion, configure a backup/retention destination and restore a staging
snapshot into another isolated database, then verify sign-in and evidence queries.

After provisioning, verify HTTPS health, registration, search/detail/research on
phone and desktop, source refresh status, and real email verification/reset with
the intended sender. Evidence and unresolved checks belong in `VERIFICATION.md`.
