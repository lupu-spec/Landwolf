# Private owner financial management — v0.13.0

Status: draft [PR #36](https://github.com/lupu-spec/Landwolf/pull/36); not deployed.
Production remains the verified v0.12.2. Both live databases reject external
inspection due to their empty IP allowlists. Network restrictions were not changed;
deployment awaits an approved internal data-preservation verification path.

## Usage

Sign in as the configured owner and choose **Finances** in the dock. Other accounts
cannot see the navigation option and receive server-side 403 for the routes.
Anonymous requests receive 401. Private API responses are not cached.

**Refresh Stripe** reads the existing live account using GET-only calls. It never
charges, cancels, changes prices or modifies customers. All available history is
paginated with limits; an incomplete read fails visibly and retains the last complete
snapshot. The dashboard shows six UTC calendar months, all-time subscription
paid-invoice collections, account receipts/refunds/fees, and active list-price
monthly/annual run-rate. These are separate measures; payouts are not sales.
Taxes, discounts, payment timing and excluded non-USD/unsupported records prevent
this management view from being audited accounting or a profit claim.

Record actual USD business expenses for Render, Spaceship, OpenAI/ChatGPT, or Other.
Positive amounts are debits; negative amounts are credits. Allocate only the business
percentage, and never duplicate Stripe fees. Identical same-day vendor/amount/reference
entries are flagged; a distinct non-sensitive reference permits genuine separate charges.
There is no deletion of existing financial history. Correct an erroneous amount with
an explicit offset entry and reference, preserving the audit trail.

Amex CSV import requires `Date,Description,Amount` headers, ISO or MM/DD/YYYY dates,
positive USD debits and negative credits, at most 100 KB and 500 rows. Preview selects
only recognized Render, Spaceship and OpenAI/ChatGPT descriptions. Review every vendor
match and allocation before confirming. Card numbers, bank credentials, complete
descriptions and unrelated personal transactions are not saved. Prefer exporting
only business rows. There is no active live Amex/bank connector; none was confirmed.
Amounts containing commas must be quoted and properly grouped. Extra/duplicate
columns or ambiguous grouping fail atomically rather than changing a charge amount.

Enter verified monthly/annual budgets and annual renewal dates. ChatGPT membership
and OpenAI API usage are separate costs. No amount is inferred from the user's plan.
Blank required vendor budgets remain unknown, and net excludes missing costs.

## Forecasts and growth actions

The next three calendar months use editable new-user, voluntary conversion, churn,
new monthly price and processing-fee hypotheses. Conservative/base/growth scenarios
vary acquisition and churn; they are not statistical predictions. Annual vendor
costs appear in their renewal month; subscription revenue uses normalized run-rate,
not exact annual renewal cash timing. Complimentary users are never assumed to
convert automatically. Graphs include zero, negatives and exact accessible tables.

The growth playbook ties recommendations to aggregate real-user/membership counts,
excluding owners and smoke tests. It proposes a measured 14-day onboarding funnel,
voluntary pilot feedback/conversion, focused acquisition cohort and cost reconciliation.
CAC, LTV, causal uplift and channel attribution are not invented without event data.
No marketing is sent and no trial policy or billing consent is changed.

## Preservation and verification

Schema 13 only adds `lw2_finance_expenses`, `lw2_finance_settings`,
`lw2_finance_snapshots` and `lw2_finance_audit`. Existing tables, identities,
billing, CRM and trial information must remain intact. Forecast settings use
optimistic revisions; failed submissions preserve form values. CSV changes invalidate
the preview, preventing stale confirmations. Logout removes financial DOM content.

Local checks: 20 frontend tests, 567 full backend tests before the final CSV
hardening, and 35 focused finance tests after it;
format/lint/types, browser build, source/wheel/package, Bandit, dependency audits,
secretlint and diff check passed. Browser launch failed because executables are
unavailable; that is not a browser pass. Disposable PostgreSQL/restore and legacy
tests await hosted CI. New tests cover owner/anonymous/nonowner boundaries, CSRF,
strict money/allocation validation, future-date rejection, import atomicity/privacy,
credits/duplicate protection, stale-plan conflict, failed refresh preservation,
GET-only Stripe reconciliation, annual normalization and forecast year rollover.

Six browser cases exercise Chromium/WebKit at 390/834/1440 px, synthetic revenue,
accessible charts, mobile input sizing, failure/retry values, CSV preview/confirmation,
duplicate recovery and logout cleanup. Their screenshots contain synthetic fixture
aggregates only, never live owner's finances. Hosted gate/deployment evidence pending.

The initial candidate `0ddc3b6820aa4d1d963777533aed370e08098d06` passed hosted
format/lint/types, frontend/backend, PostgreSQL integration and exact restore gates;
browser/build/security gates are still running. Hosted legacy run `38086909782`
passed 53 tests, and static release preflight passed in `38086909795`; conditional
production/staging preflight jobs were skipped, not passes. Final CSV hardening
requires another full candidate gate run. Staging/production acceptance is **Not run**.

## Exact local commands

From `beta/`, unless noted. Successful chained commands preserve failure exit status.

| Commands | Result |
| --- | --- |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | Passed |
| `npm run test:unit` | Passed, 20 |
| `.venv/bin/pytest -q -m 'not browser' --tb=short` | Passed, 567 before final CSV hardening; final rerun in progress |
| `.venv/bin/pytest -q tests/test_finance.py --tb=short` | Passed, 35 after CSV hardening |
| `npm run build` | Passed |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed |
| `.venv/bin/bandit -q -r landwolf`; `.venv/bin/pip-audit --local --skip-editable` | Passed |
| `npm audit --audit-level=moderate`; `npm run secrets` | Passed |
| `uv lock --check`; `git diff --check` | Passed |
| `.venv/bin/pytest -q -m browser tests/test_finance_browser.py --tb=short` | Failed launch: six cases, browser executables missing |
| `.venv/bin/python scripts/check_postgres.py`; `.venv/bin/python scripts/check_restore.py` | Not run successfully locally: disposable CI service required |
| Legacy `PYTHONPATH=. pytest -q` | Not run locally; 53 passed hosted |
