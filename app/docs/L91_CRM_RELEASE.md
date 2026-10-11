# L91 LLC CRM v0.8.0 — release verification

> For current contact-opening and mobile login behavior, see
> [the v0.9.2 mobile fix](CRM_MOBILE_FIX_RELEASE.md). Historical evidence follows.

Implementation and operator guide: [L91_LLC_CRM.md](L91_LLC_CRM.md).
Merged PR: https://github.com/lupu-spec/Landwolf/pull/24.
Final candidate CI: https://github.com/lupu-spec/Landwolf/actions/runs/37311235811.
Staging live checks: https://github.com/lupu-spec/Landwolf/actions/runs/37312219631.
Production live checks: https://github.com/lupu-spec/Landwolf/actions/runs/37312673954.

**Passed:** v0.8.0 is observed live in both environments. Staging runs candidate
`476b683bca5bc56c67984a38c49298a63673f23c`; production runs merge
`7c3dc29889c1894bce34c55db29d1a591179bd66`. Both have Git tree
`d8d132a470cecda22825abe8d8d1fcc86187c551`, so the runtime is identical.

Changes: portable CRM core, LandWolf authorization adapter, owner dock/workspace,
registration profile contract/form, additive schema 10 migration, project-scoped
intake and credentials, safe CSV, lifecycle/tags/follow-up, notes and activity.
Existing production accounts, entitlements, research, logo and infrastructure are
preserved. No paid service or runtime dependency is added.

## Commands and results

Commands below run from `beta/` unless identified otherwise. Exit 0 is a pass.
A missing tool, unavailable service, or failure is not treated as a pass.

| Command | Observed result |
| --- | --- |
| `uv sync --frozen --dev` | Passed locally, exit 0 |
| `uv lock --check`; `npm ci` | Passed locally, exit 0; application version metadata only |
| `.venv/bin/ruff format landwolf tests scripts`; `npm run format` | Passed locally; formatted diff reviewed |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed locally and hosted CI |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed locally and hosted CI |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | Passed locally and hosted CI |
| `npm run test:unit` | Passed locally and hosted CI; 15 tests |
| `.venv/bin/pytest -q tests/test_crm.py` | Passed final local run: 18 tests. First run failed one test harness call using unsupported TestClient.delete JSON parameter; corrected to request(DELETE) without changing assertions |
| `.venv/bin/pytest -q -m 'not browser'` | Passed final hosted CI: 429 tests; earlier local full suite: 428. Browser-marked tests run separately |
| `.venv/bin/python scripts/check_postgres.py` | Passed in hosted CI against disposable PostgreSQL, including CRM capture, updates, and CSV |
| `.venv/bin/python scripts/check_restore.py` | Passed in hosted CI: exact 26-table pg_dump/restore against the disposable PostgreSQL service |
| `npm run build` | Passed locally and hosted CI |
| `.venv/bin/pytest -q tests/test_crm_browser.py` | Failed locally: all four attempts failed to launch because required browser executables were absent. All four passed in final hosted full browser suite |
| `.venv/bin/playwright install --with-deps chromium webkit` | Failed locally: apt user/group changes prohibited by container permissions. Hosted installation passed |
| `.venv/bin/pytest -q -m browser` | Passed final hosted CI: 56 tests (Chromium/WebKit at 390px and 1440px), including registration-to-owner-CRM, optional field persistence, stage edit/reload, escaped notes, CSV, access denial/private state cleanup and overflow assertions |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed locally and final hosted CI |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable` | Passed locally and final hosted CI; no known dependency vulnerabilities reported |
| `npm audit --audit-level=moderate`; `npm run secrets` | Passed locally and final hosted CI |
| `PYTHONPATH=. /workspace/scratch/051463328da8/Landwolf/.venv-legacy/bin/pytest -q` (repository root, separate legacy environment) | Passed: 53 tests; legacy CI also passed |
| `LANDWOLF_DATABASE_URL=sqlite:////tmp/l91-crm-source-check.db .venv/bin/python -m landwolf.cli sync` | Passed, exit 0. Eight automated feeds ready: MN 4, AR 0, TX 31, USDA 19, Treasury 19, IRS 1, AK 170, MI 28 records. Directory-only sources remain directory-only |
| `.venv/bin/python scripts/check_hosted_staging.py --environment "$TARGET_ENVIRONMENT"` | Passed hosted runs for staging and production: exact release, HTTPS, health, correct environment/billing/mail mode, four Chromium/WebKit customer journeys and persistent-session/cache/restart/logout checks |
| `git diff --check`; `git status --short` (repository root) | Passed; intended changes only |

Initial development failures were fixed before publishing: a wrong working-directory
prefix prevented a helper script from opening files; initial unformatted sources
failed lint; TypeScript required explicit known category keys; a broad version
replacement briefly changed an unrelated lockfile entry, corrected before
`npm ci`/lock verification. CLI push had no GitHub credential; the connected
GitHub API published the exact local Git tree instead, preserving all file bytes.

Read-only production SQL via Render MCP was unavailable because the database's
external IP allowlist is empty. No network allowlist was relaxed. Production SQL
counts are not claimed as verified. Disposable database tests establish migration
behavior; hosted runtime health and customer tests establish the deployed app.

The first hosted browser run passed all 52 existing journeys but failed the four
new CRM journeys because a nested select's label included its option text. The
signup industry/role fields and CRM selectors now use explicit, separate labels.
CRM navigation was moved inside the existing nav for active-state semantics;
saving a stage refreshes list cards as well as detail. No assertion was weakened.

## Observed deployment evidence

| Environment | Render deployment | Live (UTC, 2026-10-05) | Observed verification |
| --- | --- | --- | --- |
| Staging | `dep-db1ppmqd0e5s738s9im0` | 12:50:41.658598 | Passed exact v0.8.0/candidate commit, health, HTTPS, payments disabled, customer browser/session checks; anonymous CRM contacts/projects/CSV returned 401; missing registration profile returned 422 without creating an account |
| Production | `dep-db1prh7avr4c73d2o2ag` | 12:54:15.612404 | Passed exact v0.8.0/merge commit, health, HTTPS, existing live billing mode, customer browser/session checks |

Render error-log queries returned no entries for staging 12:50–12:54 UTC and
production 12:54–13:00 UTC. An earlier staging log query failed with the provider's
Loki timeout; the narrower retry succeeded. This is a bounded log review, not a
claim that no future errors can occur.

The initial quick ledger smoke (run 37312673700) **failed** because its checkout
still described v0.7 while staging already ran v0.8. The ledger is reconciled only
after observing both new deployments. Independent exact-release hosted checks
passed. The documentation-only ledger update does not redeploy either runtime;
auto-deploy remains disabled. No accounts or database were reset and no
infrastructure or billing settings were changed.

## Verification limits

**Not run:** live owner-session CRM interaction, direct production SQL counts,
physical iPhone/iPad keyboard and assistive technology testing. The owner workflow
is covered with isolated synthetic data in real hosted browsers. No owner or real
subscriber was impersonated and no payment was initiated. Each environment's
hosted smoke retained one explicitly disposable, non-cohort verification account.

**Not run:** manual visual review of CRM screenshots. The full hosted browser
artifact exceeded the file download size limit. The cloud browser and direct
workspace requests to production returned a workspace-visible "Site Unavailable"
page, so these are not successful production HTTP or visual checks. Independent
GitHub-hosted production checks above completed successfully. Staging browser
evidence was downloaded; automated layout and behavior assertions passed in CI.
Browser emulation is not a physical-device test.

Live staging research returned partial coverage under the existing availability
contract; this CRM change does not expand source coverage. Profile correction or
deletion remains an owner operational procedure. No marketing email is sent by
this release. No separate external project is connected until its backend calls
the documented intake API. The schema-10 migration is additive; the old v0.7 app
rejects schema 10, so rollback requires a compatible fix forward or coordinated
backup restoration, not dropping contact data.
