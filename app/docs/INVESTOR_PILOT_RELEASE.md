# Investor feedback pilot release — 2026-10-04

- **Live version:** `0.4.0-beta.7`
- **Immutable runtime commit:** `4f52057d6499d420f6cfce6a9e97b1baa29d0dfe`
- **Published branch:** `codex/investor-feedback-pilot`
- **Merged PR:** https://github.com/lupu-spec/Landwolf/pull/11

The user authorized publishing to this repository and deploying through Render's
My Workspace after the remaining checks passed. The existing rebuilt application,
database, accounts and production domain were retained. No legacy service or
`main` branch was deployed.

## Observed deployments

| Environment | Render deployment | Live UTC | Observed version / commit |
| --- | --- | --- | --- |
| Staging | `dep-db1alfh42hec73epuo7g` | 2026-10-04 19:37:40 | `0.4.0-beta.7` / `4f52057d6499d420f6cfce6a9e97b1baa29d0dfe` |
| Production | `dep-db1amtou01pc73djnmm0` | 2026-10-04 19:40:41 | `0.4.0-beta.7` / `4f52057d6499d420f6cfce6a9e97b1baa29d0dfe` |

Render reported both deployments live. Hosted checks independently verified the
exact `/api/version` payload, `/api/health`, environment, HTTPS, authentication,
CSRF rejection, disabled billing/mail and the production www redirect. Render
logs reported schema v7 ready at 19:37:17 UTC in staging and 19:40:25 UTC in production.

- Staging evidence: https://github.com/lupu-spec/Landwolf/actions/runs/37228923125
- Production evidence: https://github.com/lupu-spec/Landwolf/actions/runs/37229118822
- Required candidate gates: https://github.com/lupu-spec/Landwolf/actions/runs/37228598183
- Legacy tests: https://github.com/lupu-spec/Landwolf/actions/runs/37228598185
- Static preflight tests: https://github.com/lupu-spec/Landwolf/actions/runs/37228598180

## Changes and operation

Owner-managed invitations require an existing account. Participants explicitly
accept terms and submit a baseline survey. Access lasts exactly three calendar
months from acceptance; later surveys cannot reset the clock. In-app check-ins
are due on days 14, 30, 60 and 85, with up to seven days of grace capped at expiry.
Overdue feedback pauses protected features; completion restores access during
the original term. Saved Hunts, feedback and account recovery remain accessible.

Schema v7 adds enrollment, response and audit tables. Server-side authorization,
CSRF checks, transaction serialization and account-scoped responses protect the
workflow. Independent owner/complimentary overrides remain explicit. No global
paywall, payment collection, automatic charges or email survey delivery was added.

The browser checks exposed a startup race that could replace an early Hunt tab
selection. Navigation now appears after feedback initialization. A delayed-response
browser regression covers the fix. The navigation assertion now includes Feedback.
Locked audit fixes also update brace-expansion, fast-uri and urllib3 patch versions.
See [operating instructions](INVESTOR_PILOT.md) for the owner workflow and API.

## Commands and outcomes

All commands below completed successfully in the hosted candidate gate unless
otherwise identified. Commands run from `beta/` except the two root pytest entries.

| Commands | Result |
| --- | --- |
| `uv sync --frozen --dev`; `npm ci`; `.venv/bin/playwright install --with-deps chromium webkit` | **Passed** — locked environments and browser binaries installed |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | **Passed** |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | **Passed** |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | **Passed** — 24 Python modules checked |
| `npm run test:unit` | **Passed** — 9 tests |
| `.venv/bin/pytest -q -m 'not browser'` | **Passed** — 315 tests; browser tests selected separately |
| `.venv/bin/python scripts/check_postgres.py` | **Passed** — disposable PostgreSQL 18, migrations, retained account/session fixtures, cohort consent/replay, overdue gate and survey restoration |
| `.venv/bin/python scripts/check_restore.py` | **Passed** — dump/restore with exact row digests across 19 populated/schema tables |
| `npm run build`; `.venv/bin/pytest -q -m browser` | **Passed** — 28 browser journeys, including mobile/desktop consent and overdue-survey restoration |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | **Passed** — wheel/runtime/assets and source archive checks |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable`; `npm audit --audit-level=moderate`; `npm run secrets` | **Passed** — no reported scanner findings or known dependency vulnerabilities |
| `git diff --check`; `git status --short` | **Passed** — no whitespace errors or unexpected tracked changes in the candidate gate |
| Root `PYTHONPATH=. pytest -q` | **Passed** — 53 legacy tests |
| Root `PYTHONPATH=. pytest -q tests/unit/test_deployment_preflight.py` | **Passed** — 11 static preflight tests |
| `.venv/bin/python scripts/check_hosted_staging.py --environment staging` | **Passed** — four live Chromium/WebKit journeys at 390px and 1440px |
| `.venv/bin/python scripts/check_hosted_staging.py --environment production` | **Passed** — four live Chromium/WebKit journeys at 390px and 1440px |

`uv lock --check` passed locally after the dependency edits. Local format, lint,
types, frontend tests and build were rerun after the navigation fix. The hosted
gate above is the complete verification of the final runtime revision.

## Retained failures and limits

- **Resolved:** local browser installation failed because the download was truncated;
  local PostgreSQL/Docker was unavailable. Hosted browser, PostgreSQL and restore
  gates replaced these missing local checks; they were not counted as local passes.
- **Resolved:** initial hosted browser run 37227813812 failed two navigation races
  and two outdated navigation-count assertions. Run 37228279314 then exposed
  CSP-unsafe evaluation in the new test harness. The harness now observes a DOM
  attribute; the application's CSP was not relaxed. Final run 37228598183 passed.
- **Resolved in the record update:** the old release ledger caused the push-triggered
  `live-smoke.yml` checks to compare against historical versions before this rollout.
  The current-environment rows now identify the independently observed live runtime.
- **Separate legacy workflow:** pre-existing misindentation in `release.yml` caused
  workflow validation failures. Its jobs are now correctly nested and its unimplemented
  deploy placeholder explicitly exits with failure. Local YAML structure, job dependency
  and manual-trigger checks passed. This legacy Stripe workflow was not used for this
  release; its environment jobs were not run. Rebuilt LandWolf billing remains disabled.
- **Recovery scope:** the existing production PostgreSQL instance was available on
  paid `basic_256mb` compute. Render documents continuous PITR for paid databases at
  https://render.com/docs/postgresql-backups. The connector does not expose the exact
  recovery window/export inventory. Restore was rehearsed only on the disposable CI
  database; no production restore was attempted. The database's private network
  restrictions were retained when the read-only connector could not reach it.
- **Observed source limits:** Minnesota DOT, Treasury and IRS feeds reported unavailable;
  Texas GLO was syncing. Arkansas, USDA, Alaska and Michigan were ready. Research
  reported partial coverage. These observations do not establish nationwide availability.
- **Not exercised live:** owner-account login, invitation of a real participant and
  clock-advanced cohort expiry. Authorization and full participant transitions passed
  isolated tests. A valid existing `LANDWOLF_OWNER_ACCOUNT_ID` is required for the owner
  controls; that binding was not changed or independently inspected during this rollout.
- One synthetic non-cohort `example.com` account was retained in each environment by
  the hosted smoke tests. No real investor was enrolled, no outreach was sent, and no
  owner credentials, survey responses, cookies or passwords were written to artifacts.

Documentation and workflow-only commits after the runtime commit do not imply a
new deployment. Render auto-deploy remains off for both rebuilt services.
