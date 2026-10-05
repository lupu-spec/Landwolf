# L91 LLC CRM v0.8.0 — release verification

Implementation and operator guide: [L91_LLC_CRM.md](L91_LLC_CRM.md).
Candidate PR: https://github.com/lupu-spec/Landwolf/pull/24.

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
| `.venv/bin/pytest -q tests/test_crm.py` | First run: 16 passed, one test harness failure from an unsupported TestClient.delete JSON parameter; corrected to request(DELETE) without changing assertions |
| `.venv/bin/pytest -q -m 'not browser'` | Passed locally: 428 tests; browser-marked tests deliberately run separately |
| `.venv/bin/python scripts/check_postgres.py` | Passed in hosted CI against disposable PostgreSQL, including CRM capture, updates, and CSV |
| `.venv/bin/python scripts/check_restore.py` | Passed in hosted CI against the disposable PostgreSQL service |
| `npm run build` | Passed locally and hosted CI |
| `.venv/bin/pytest -q tests/test_crm_browser.py` | Unavailable locally: all four attempts failed to launch because required browser executables were absent |
| `.venv/bin/playwright install --with-deps chromium webkit` | Failed locally: apt user/group changes prohibited by container permissions. Hosted installation passed |
| `.venv/bin/pytest -q -m browser` | Hosted result pending |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed locally |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable` | Passed locally; no known dependency vulnerabilities |
| `npm audit --audit-level=moderate`; `npm run secrets` | Passed locally |
| `PYTHONPATH=. /workspace/scratch/051463328da8/Landwolf/.venv-legacy/bin/pytest -q` (repository root, separate legacy environment) | Passed: 53 tests; legacy CI also passed |
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

## Remaining release checks

Hosted browser suite, visual review, staging deployment/health/browser check,
production promotion/health/browser check, and runtime error-log scan are pending.
Physical iPhone/iPad keyboard and assistive technology checks are not run. Browser
emulation is not a physical-device test. No separate external project is connected
until its backend calls the documented intake API.
