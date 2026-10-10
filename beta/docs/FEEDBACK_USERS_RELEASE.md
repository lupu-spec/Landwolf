# v0.5.1 — private feedback user list and CSV export

The Feedback account list, submitted responses, and new **Export users CSV**
button use the existing configured owner authorization. LandWolf currently has
one owner privilege, not a separate assignable administrator role. Paid access,
complimentary access, and investor participation do not grant this privilege.
Ordinary users retain their own feedback forms and status.

The browser clears private account details when feedback authorization cannot be
confirmed, export authorization fails, or the account signs out. Requests from an
old session cannot repopulate the list or initiate a download. Server checks apply
to every CSV request; UI visibility is not the authorization boundary.

CSV contains email, account role, and pilot invitation/acceptance/end/revocation
UTC dates. It contains no passwords, session tokens, billing details, or survey
answers. UTF-8 with a BOM, standard CSV quoting, and spreadsheet formula protection
support spreadsheet use. The export includes registered users beyond the table's
500-row display limit, up to 10,000; larger exports fail explicitly without a
partial file. Responses cannot be cached. Storage failures return a retryable
error and do not download an error page as a CSV.

The filename is `landwolf-users-YYYY-MM-DD.csv`. Browser/device settings determine
whether it goes to Downloads or prompts for a destination; a website cannot force
a filesystem folder. Desktop/mobile Chromium and WebKit automation validates the
browser download; physical-device and spreadsheet-application checks are not run.

No database migration, dependency upgrade, billing change, or authentication
lifetime change. Schema remains 9. **Live in staging and production.**
[PR #21](https://github.com/lupu-spec/Landwolf/pull/21) merged as
`32b3fcf0ebbe6507e7f7142262cb94930b4439e8`; the exact staging-tested commit was
promoted to production. Deployment evidence is recorded below.

## Verification

Commands run from `beta/` except the repository-root checks.
[Final candidate CI 37282901379](https://github.com/lupu-spec/Landwolf/actions/runs/37282901379)
passed all release gates on `ff2e5e2aaa3456622861b56815563105a6f92e3c`.
[Legacy tests](https://github.com/lupu-spec/Landwolf/actions/runs/37282901399) and
[static release preflight](https://github.com/lupu-spec/Landwolf/actions/runs/37282901476) also passed.
Successful commands exited 0. The merged runtime tree matches the tested tree exactly.

| Command | Result |
| --- | --- |
| `uv lock --check`; `npm ci` | Passed, exit 0 |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed, exit 0 |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed, exit 0 |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | Passed, exit 0 |
| `npm run test:unit` | Passed, 9 tests, exit 0 |
| `.venv/bin/pytest -q tests/test_feedback_export.py` | Passed, first 14 cases, exit 0; expanded suite included below |
| `.venv/bin/pytest -q -m 'not browser'` | Passed, 411 tests, exit 0; 40 browser cases run separately in hosted CI |
| `.venv/bin/python scripts/check_postgres.py`; `.venv/bin/python scripts/check_restore.py` | Passed hosted: PostgreSQL integration and exact restore digests across 23 tables. Not run locally: no disposable PostgreSQL service |
| `npm run build` | Passed, exit 0 |
| `.venv/bin/pytest -q -m browser` | Passed hosted: all 40 Chromium/WebKit cases, including four owner CSV/privacy journeys at 390px and 1440px. Not run locally: browser archives previously failed to install |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed, exit 0 |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable` | Passed, exit 0 |
| `npm audit --audit-level=moderate`; `npm run secrets` | Passed, exit 0 |
| `PYTHONPATH=. .venv-legacy/bin/pytest -q` (root) | Passed, 53 legacy tests, exit 0 |
| `LANDWOLF_DATABASE_URL=sqlite:////tmp/landwolf-feedback-release-sources.db .venv/bin/python -m landwolf.cli sync` | Passed, exit 0; all eight implemented feeds ready in isolated local snapshot |
| `git diff --check`; `git status --short` (root) | Passed, intended files only, exit 0 |

Resolved initial lint failure: Ruff requested splitting the Hypothesis imports;
fixed before the final gates. Initial interpreter version probe used a nonexistent
root `.venv`; all verification uses the application's `beta/.venv` and isolated
legacy environment. Existing FastAPI/httpx deprecation warnings are unrelated.

The first hosted run, [37282035075](https://github.com/lupu-spec/Landwolf/actions/runs/37282035075),
passed backend, PostgreSQL and 23-table restore checks plus all 36 existing browser
cases. Four new browser cases failed before navigating: Playwright cannot attach
its wrapper metadata to Python's built-in `list.append` callback. A normal lambda
callback fixes the test harness; no assertions or runtime code were changed.
The complete hosted rerun above passed before deployment.

## Operations and limitations

Both existing services retain their databases, branch configuration, disabled
automatic deployment, and payment settings. Production PostgreSQL was confirmed
available on its existing paid plan; prior same-session successful backup-marker
and WAL archives at 07:04 and 07:14 UTC remain the latest observed backup evidence.
The attempted log refresh returned Render log-service HTTP 503/504; this is not
represented as a successful new backup check. No schema change or restore is made.
The full disposable 23-table recovery rehearsal passed on the candidate.

CSV success is tested using synthetic owner/user accounts in CI. Live checks use
new ordinary fixture accounts to prove hidden/empty private UI and API denial;
they do not sign in as the real owner or export real customer data. Downloads on
physical devices, spreadsheet application behavior, and manual screenshot review
are not independently verified. Existing partial source coverage remains; the
local source check does not prove every production source-state row is current.

## Observed deployments — 2026-10-05 UTC

| Environment | Version / runtime commit | Render deployment | Live UTC | Independent live checks |
| --- | --- | --- | --- | --- |
| Staging | v0.5.1 / `32b3fcf0ebbe6507e7f7142262cb94930b4439e8` | `dep-db1lua6gekts73efmfu0` | 08:27:15 | [37283622154](https://github.com/lupu-spec/Landwolf/actions/runs/37283622154), passed before production promotion |
| Production | v0.5.1 / `32b3fcf0ebbe6507e7f7142262cb94930b4439e8` | `dep-db1lvvu0tbcc73bg1re0` | 08:30:53 | [37283604371](https://github.com/lupu-spec/Landwolf/actions/runs/37283604371), passed |

Both live commands passed with the immutable runtime commit as `GITHUB_SHA`:

- `.venv/bin/python scripts/check_hosted_staging.py --environment staging`
- `.venv/bin/python scripts/check_hosted_staging.py --environment production`

They assert exact release identity, HTTPS/database health, the existing billing
mode, anonymous CSV rejection, signed-in ordinary-user rejection for every private
feedback endpoint, and an empty/hidden admin section without an export button.
Each environment passed four customer journeys (Chromium/WebKit, 390px/1440px),
plus persistent-session, browser-restart, cache-clear and explicit-logout checks.
Production also verifies the live payment gate and www redirect. Tests do not
create payments or change owner privileges. Required owner download success and
error/retry flows use synthetic fixtures in the full CI browser suite.

Release documentation is published separately after these observations; it does
not change the deployed runtime commit or require another deployment.
