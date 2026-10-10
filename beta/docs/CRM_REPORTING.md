# CRM account categories and user statistics

Live v0.10.1 in production and staging, October 10, 2026.

Open **L91 LLC CRM** to see Users, Trial users and Paid users. Click any count to
show the matching accounts. **Account category** separates Users, Owners, Smoke
tests, and unregistered/external-project contacts. The default **People (hide
smoke tests)** keeps real contacts and the owner visible. Select **User** for
registered LandWolf accounts that are neither the owner nor a recognized test.
Use **Membership** to filter trial/paid status, and **Export contacts CSV** to
download that exact filtered list with category, membership and billing-sync time.

Smoke tests are retained in their own category, excluded from default lists and
exports, and never included in user/trial/paid statistics. Select **Smoke test**
or **All records, including smoke tests** to inspect them. No accounts are deleted,
suspended, granted access, or billed by classification. Categories are recomputed
from existing facts on every read, so existing and future test accounts are handled
automatically without a recurring job or new service.

## Counting rules

| Category | Rule |
| --- | --- |
| Owner | The configured immutable owner account ID; takes precedence over test detection |
| Smoke test | LandWolf contacts matching the known test identities below |
| User | A linked, email-matched LandWolf account that is neither owner nor smoke test |
| Contact / external project | Unregistered contacts and contacts managed by another project |
| Paid user | Stored Stripe subscription status is active and paid-through time is in the future |
| Trial user | Current owner trial grant, accepted unexpired feedback pilot (including feedback overdue), or stored Stripe trialing status |
| Complimentary | A current owner grant that is not a matching current trial reservation |
| Trial invited / reserved | A trial reservation, unaccepted pilot invitation, or not-yet-claimed configured pilot reservation |
| Trial ended | A previous trial/pilot without current paid, trial or complimentary status |
| Billing needs attention | Stored past-due, unpaid, incomplete or paused Stripe status without another current access category |
| Registered, no active plan | Other registered users, including a subscription without current paid-through coverage |

Paid takes precedence over trial, so a customer with both is counted once as paid.
The membership categories sum to Users. Suspended subscribers still count according
to their billing record: suspension does not cancel their subscription. Counts are
not revenue, an invoice ledger, a historical conversion metric or proof of payment.
Reporting does not call Stripe or activate reservations. The view shows the report
time and warns if billing records are over 24 hours old. Normal webhooks and the
existing billing refresh continue to update the stored facts.

Counts follow project, search, stage, industry and primary-use filters, before
account-category and membership filtering. Owners and tests are always excluded
from Users, Trial users and Paid users. Unregistered contacts are not trial users
merely because access has been reserved for them.

## Conservative automatic test detection

The recognized prefixes are `production-smoke-`, `staging-smoke-`, `smoke-`,
`hunt-save-qa-`, `hunt-browser-qa-`, `deployment-check-`,
`national-deployment-check-`, `free-api-check-`, `domain-check-`, `qa-saved-`,
`qa-navigation-` and `qa-retirement-`, only on reserved `example.com` or
`example.invalid` addresses. The older patterns were confirmed in a read-only
production audit (12 legacy verification accounts). The exact support Gmail plus alias used for the
October 10 recovery verification is also recognized. A real email address or
name containing “test,” “smoke” or “QA” is not enough. Detection is limited to the
LandWolf project; other projects retain their own account meaning. A previously
unknown testing convention needs a reviewed rule rather than a broad name match.

## Owner and operational interfaces

- `GET /api/admin/crm/contacts` and `.csv`: `account_category=people` by default;
  supported alternatives `all`, `user`, `owner`, `smoke_test`, `contact`.
- `membership=paid` or `trial` selects matching users; additional keys are listed
  in the project's categories response. Invalid values return 422.
- `GET /api/admin/crm/statistics`: aggregate counts for all CRM records.
- `python -m landwolf.cli crm-summary`: aggregate-only read-only operational job.
  Run in the existing service environment. It prints no emails or credentials,
  performs no schema bootstrap or external requests, and changes no records.

All HTTP reporting endpoints retain server-side owner authorization. Test status
is a reporting label, never an authentication role or entitlement. Filtering happens
before pagination and CSV limits. The 10,000-row CSV bound and formula escaping
are preserved. Private counters and records are cleared at sign-out or lost owner
authorization. There is no schema migration, dependency change or billing change.

## Production job result — 2026-10-10 03:54:29 UTC

`python -m landwolf.cli crm-summary` completed successfully in the existing
production Render service after deployment. It returned these aggregate counts:

| Category | Count |
| --- | ---: |
| Users (excluding owner and tests) | 5 |
| Active trial users | 0 |
| Paid users | 0 |
| Trial invited / reserved | 2 |
| Registered, no active plan | 3 |
| Complimentary / trial ended / billing attention | 0 each |
| Owner | 1 |
| Smoke-test records, hidden by default | 29 |
| Unregistered / external-project contacts | 1 |

Two customer billing records were over 24 hours old; the oldest sync was
2026-10-05 03:08:36 UTC. These are stored-record statistics, not a new Stripe
reconciliation or proof of payment. The UI displays the stale-record warning.
Known future smoke-test accounts are classified automatically when read. This job
changed no customer records, credentials, entitlements or billing configuration.
An earlier report at 03:52:36 UTC counted 28 tests. The final release browser check
added one known test account; rerunning the report confirmed it was automatically
hidden while customer totals and memberships remained unchanged.

## Release verification — 2026-10-10 UTC

PR [#28](https://github.com/lupu-spec/Landwolf/pull/28) merged as
`a3998b525530a845dedd66b52c401c0cb50b7d51`. Its tree
`0a11856adfa530464ebd6258c7ffc9f7c999be2d` exactly matches the tested staging
candidate `24dee28c3fa2d05de1b1951767b1fa37fcbbc5a2`.

| Environment | Version / runtime commit | Render deployment | Observed live UTC |
| --- | --- | --- | --- |
| Staging | v0.10.1 / `24dee28c3fa2d05de1b1951767b1fa37fcbbc5a2` | `dep-db4r645ckfvc73fv9qi0` | 2026-10-10 03:39:02 |
| Production | v0.10.1 / `a3998b525530a845dedd66b52c401c0cb50b7d51` | `dep-db4rb4nlot8c73co0940` | 2026-10-10 03:49:25 |

All commands below **Passed**, exit 0, on the final candidate in
[full gate run 38021241051](https://github.com/lupu-spec/Landwolf/actions/runs/38021241051):

- `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check`.
- `.venv/bin/ruff check landwolf tests scripts`; `npm run lint`.
- `.venv/bin/mypy landwolf`; `npm run typecheck`.
- `npm run test:unit` — 16 tests.
- `.venv/bin/pytest -q -m 'not browser'` — 510 tests.
- `.venv/bin/python scripts/check_postgres.py` — disposable PostgreSQL integration,
  including the new classification and membership queries.
- `.venv/bin/python scripts/check_restore.py` — exact 29-table dump/restore.
- `npm run build`; `.venv/bin/pytest -q -m browser` — 78 tests, including four
  new Chromium/WebKit phone/desktop CRM reporting, filters, CSV and privacy flows.
- `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py`.
- `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable`;
  `npm audit --audit-level=moderate`; `npm run secrets`.
- `git diff --check`; `git status --short`.

Locked CI installation (`uv sync --frozen --dev`, `npm ci`, Playwright Chromium
and WebKit installation) passed. The independent legacy `PYTHONPATH=. pytest -q`
passed (53 tests) in [run 38021241045](https://github.com/lupu-spec/Landwolf/actions/runs/38021241045).
Release preflight also passed. Locally, final formatting/lint/types checks,
`.venv/bin/pytest -q tests/test_crm_reporting.py tests/test_version.py` (29 tests),
`uv lock --check`, and diff checks passed. Phone Chromium and desktop WebKit
CRM evidence images were visually reviewed; no horizontal overflow was observed.

Staging `.venv/bin/python scripts/check_hosted_staging.py --environment staging`
passed in [run 38021239425](https://github.com/lupu-spec/Landwolf/actions/runs/38021239425).
It verified the exact deployed identity, HTTPS, health, mail/payment mode, four
live customer journeys, session persistence, and authorization boundaries.
Production origin checks observed exact version/commit, healthy state and enabled
payments; unauthenticated CRM statistics returned 401. Production
`.venv/bin/python scripts/check_hosted_staging.py --environment production`
**Passed** on attempt 2 of
[run 38021861470](https://github.com/lupu-spec/Landwolf/actions/runs/38021861470),
at 03:53:42 UTC: exact release/HTTPS and expected billing/mail mode, four
Chromium/WebKit phone/desktop login/paywall/privacy/logout journeys, and persistent
cookie/cache-clear/browser-restart/logout checks. It retained one disposable test
account, automatically classified as a hidden smoke test.

Before promotion, Render Recovery showed an enabled Restore database control and
a three-day recovery window. No backup, network, environment variable or security
configuration was changed. Schema 11, Gmail recovery, Stripe, trial grants, pilot
access, source allowlists, snapshots and quarantine protections are preserved.

**Failed, unrelated:** live source verification
`LANDWOLF_DATABASE_URL=sqlite:////tmp/landwolf-crm-release-source-check.db LANDWOLF_AUTO_SYNC=false .venv/bin/python -m landwolf.cli sync`
exited 1 because Arkansas COSL returned HTTP 500 at its official
`https://cosl.org/Home/Contents` publisher URL. Seven other listing adapters were
ready. This disposable check did not modify production source data.

**Not run locally:** browser and PostgreSQL/restore gates, because this workspace
has no installed browser executables or disposable PostgreSQL service. The final
hosted gates above ran and passed these checks. Local custom-domain access is
limited by the runner; hosted checks validate the public domain. Two existing
Starlette deprecation warnings remain. No physical-device test was performed.

The first production hosted attempt overlapped rollout: API identity was new but
the browser still displayed v0.9.3. It was retried after Render confirmed the
deployment live. The initial ledger smoke job failed because the ledger still
described the previous releases; live identities are recorded only after observation.
