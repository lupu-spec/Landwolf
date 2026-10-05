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
lifetime change. Schema remains 9. Production deployment and hosted checks are
pending; the running release remains v0.5.0 until observed and recorded.

## Verification

Commands run from `beta/` except the two repository-root checks. Results will be
updated after the complete candidate gates and live checks finish.

| Command | Result |
| --- | --- |
| `uv lock --check`; `npm ci` | Passed, exit 0 |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed, exit 0 |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed, exit 0 |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | Passed, exit 0 |
| `npm run test:unit` | Passed, 9 tests, exit 0 |
| `.venv/bin/pytest -q tests/test_feedback_export.py` | Passed, first 14 cases, exit 0; expanded suite included below |
| `.venv/bin/pytest -q -m 'not browser'` | Passed, 411 tests, exit 0; 40 browser cases reserved for hosted CI |
| `.venv/bin/python scripts/check_postgres.py`; `.venv/bin/python scripts/check_restore.py` | Not run locally: no disposable PostgreSQL service; required in hosted CI |
| `npm run build` | Passed, exit 0 |
| `.venv/bin/pytest -q -m browser` | Not run locally: browser installation previously failed with invalid archives; required in hosted CI |
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
A complete hosted rerun is required before deployment.
