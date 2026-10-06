# L91 LLC CRM owner administration — v0.9.0 candidate

The owner can add contacts before registration, edit profile details, correct
login emails, manage trial/complimentary access and feedback pilot invitations,
suspend/restore users, revoke sessions, and request account recovery mail.
Manual contacts now attach to later registration without duplicate-email failures.

Schema 11 adds account restrictions, access reservations and account audit storage.
Existing accounts, Stripe subscriptions, pilot terms and billing audit contracts
are preserved. Trial reservations require verified email before automatic redemption;
explicit owner grants to registered accounts remain available. Configured email
delivery is required for password-reset/verification mail. No new dependency or
paid service is added. Detailed operation: [L91_LLC_CRM.md](L91_LLC_CRM.md).

## Verification

Local candidate implementation: `cbbdca8509024c633516be6e616ecad1615d695f`, branch
`codex/crm-account-administration`, based on `9bbc9f0`. These results were observed
on 2026-10-06. The candidate has **not** been published or deployed. Existing
production/staging rows in `RELEASES.md` remain the last observed deployments.

Commands below ran from `beta/` unless noted. **Passed** means exit 0; **Failed**
and **Not run** are retained separately. Documentation-only updates follow the
tested implementation commit.

| Command | Result |
| --- | --- |
| `uv lock --check` | **Passed**. |
| `npm ci` | **Passed**; 191 packages. |
| `uv sync --frozen --dev` | **Passed**; local package version 0.9.0. |
| `.venv/bin/ruff format landwolf tests scripts` | **Passed**. |
| `npm run format` | **Passed**. |
| `.venv/bin/ruff format --check landwolf tests scripts` | **Passed**; 75 files. |
| `npm run format:check` | **Passed**. |
| `.venv/bin/ruff check landwolf tests scripts` | **Passed**. |
| `npm run lint` | **Passed**. |
| `.venv/bin/mypy landwolf` | **Passed**; 33 files on the final run after clearing a broken incremental cache. An earlier run crashed internally. |
| `.venv/bin/mypy --no-incremental landwolf` | **Passed**; 33 files. |
| `npm run typecheck` | **Passed**. |
| `npm run test:unit` | **Passed**; 15 tests. |
| `.venv/bin/pytest -q tests/test_crm_admin.py tests/test_crm.py` | **Passed**; 32 tests on the final focused run. |
| `.venv/bin/pytest -q -m 'not browser'` | **Passed**; final run 443 passed, 62 deselected, 2 dependency deprecation warnings in 79.43 seconds. Earlier run: 442 passed, 1 failed because a migration test hardcoded the former schema number. |
| `.venv/bin/pytest -q tests/test_decisions.py::test_real_v8_migration_is_additive_and_idempotent` | **Passed** after changing the expected current version to `SCHEMA_VERSION`. |
| `npm run build` | **Passed**. |
| `.venv/bin/pytest -q tests/test_crm_admin_browser.py -x` | **Failed**, exit 1: Chromium executable absent; the first browser could not launch. No browser journey completed. |
| `.venv/bin/playwright install chromium webkit` | **Failed**, exit 1: repeated browser downloads returned truncated/non-ZIP content. |
| `.venv/bin/pytest -q -m browser` | **Not run** in full: browser executables unavailable. Hosted CI must complete all 62 browser cases, including six new account administration journeys. |
| `.venv/bin/python scripts/check_postgres.py` | **Not run**: requires the designated disposable `landwolf_ci` PostgreSQL service in hosted CI. |
| `.venv/bin/python scripts/check_restore.py` | **Not run**: same disposable CI service required; no production database is used for this check. |
| `.venv/bin/python -m build` | **Passed**; version 0.9.0 source distribution and wheel. |
| `.venv/bin/python scripts/check_package.py` | **Passed**. |
| `.venv/bin/bandit -r landwolf` | **Passed**; no findings. |
| `.venv/bin/pip-audit --local --skip-editable` | **Passed**; no known vulnerabilities. |
| `npm audit --audit-level=moderate` | **Passed**; no vulnerabilities. |
| `npm run secrets` | **Passed**. |
| `PYTHONPATH=. /workspace/scratch/051463328da8/Landwolf/.venv-legacy/bin/pytest -q` (repository root) | **Passed**; 53 tests after repairing that existing environment's broken Python executable link. Initial invocation failed with exit 127. |
| `LANDWOLF_DATABASE_URL=sqlite:////tmp/l91-crm-admin-source-check.db .venv/bin/python -m landwolf.cli sync` | **Passed** using a dedicated local database; eight automated feeds returned ready records. |
| `git diff --check` (repository root) | **Passed**. |
| `git status --short` (repository root) | **Passed**; implementation worktree clean after commit. |

The source check returned ready records for MnDOT (4), Arkansas COSL (2), Texas
GLO (31), USDA resales (19), Treasury (17), IRS (1), Alaska DNR (170) and Michigan
DNR (28). This does not establish production database state or nationwide coverage.

Resolved development failures: an account event initially violated the existing
billing-only audit constraint; account administration now has additive dedicated
audit storage while billing events retain their existing contract. A test-helper
parameter collision and a fixture's premature live-billing startup were corrected
without weakening assertions. The prior schema migration test now references the
current schema constant and still checks additive/idempotent migration behavior.
Both the nonincremental and configured mypy commands passed after cache cleanup.

## Remaining release gates

`git push -u origin codex/crm-account-administration` was blocked by automatic
approval review: publishing CRM source to GitHub requires explicit authorization
for that upload. No hosted checks, pull request, staging deployment or production
deployment have run for this candidate. This is an approval block, not a successful
push or a normal command exit status.

After approval, publish to `lupu-spec/Landwolf`, run the repository CI (including
PostgreSQL, backup/restore and Chromium/WebKit), deploy to the existing isolated
Render staging service, verify exact version/commit/health and browser journeys,
then promote to the existing production service and repeat live checks. Record
the observed commit, deployment ID and UTC time for each environment. Never reset
either database or reuse a version for changed deployed code.

Mail actions require configured delivery; no real user mail has been sent. Trials
can be reserved before registration, but automatic activation requires verified
email. Paid subscriptions are displayed from the existing synchronized billing
record; access revocation or suspension does not cancel Stripe billing. The owner
login/access is protected from these administrative controls. No real user's
account, reservation, subscription or session was changed by these local tests.

## Follow-on customer account help

The same unpublished v0.9.0 candidate now includes Romulus/Remus password-reset
requests and self-service CRM profile updates. The original owner implementation
results above remain historical evidence; [the follow-on report](WOLF_ACCOUNT_HELP_RELEASE.md)
records verification after the additional code changes. Publication approval and
the remaining hosted/deployment gates still apply.
