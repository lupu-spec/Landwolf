# v0.4.4 — persistent sign-in

## Behavior

Replaces the 30-minute idle limit and eight-hour maximum session with a rolling
365-day sign-in. Login and registration set a persistent HttpOnly cookie with
Max-Age and Expires. Each app load calls `/api/session`, which renews the cookie
and existing database session together. Unexpired old cookies upgrade on return;
expired/deleted cookies require one fresh sign-in. Reminder polling does not renew
the session. `LANDWOLF_SESSION_DAYS` accepts 1–400 days, default 365; old hour/idle
settings are retired.

Browser restarts and cache-only clearing retain sign-in. Cookie/site-data deletion,
private-browsing cleanup, browser privacy policies, or more than a year without
renewal can still require sign-in. There is no credential copy in localStorage,
sessionStorage, cache storage, a fingerprint, or a hidden recovery cookie.
The upper limit respects Chrome's documented
[400-day cookie cap](https://developer.chrome.com/blog/cookie-max-age-expires).

Logout, password reset and server revocation remove the database session. Renewal
updates only an existing unexpired row, so it cannot recreate a revoked session.
Expired sessions cannot be renewed. HTTPS Secure, HttpOnly, SameSite=Strict, CSRF,
origin enforcement, hashed server tokens, billing entitlements and owner-only
coverage remain in place. Search/Hunt matching, schema 8, dependencies and deployed
infrastructure were not changed.

## Changes

- `landwolf/auth.py`, `config.py`, `main.py`: persistent cookie lifetime and guarded
  session renewal; default session policy.
- `tests/test_security.py`, `test_recovery.py`, `test_feedback.py`: inactivity and
  legacy-cookie renewal, expiry, deletion, concurrent revocation, logout/password
  reset, bounded lifetime, and polling behavior.
- `tests/test_browser.py`: actual Chromium/WebKit profile close/relaunch, cache
  clearing, cookie deletion and logout persistence without storage-state injection.
- `scripts/check_postgres.py`: database renewal with stale activity and a valid
  nearly expired session. `check_hosted_staging.py`: live restart/cache/logout checks.
- Runtime version/package/lock project metadata and catalog User-Agent: v0.4.4.
  README documents the supported behavior and limitations.

## Local command results

Commands run from `beta/` unless labeled otherwise. **Passed** means exit 0.

| Command | Result |
| --- | --- |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | Passed; 26 Python modules |
| `.venv/bin/pytest -q tests/test_security.py tests/test_feedback.py tests/test_recovery.py tests/test_coverage_access.py tests/test_live_billing.py` | Passed; 79 tests before the final regression addition |
| `npm run test:unit` | Passed; 9 tests |
| `.venv/bin/pytest -q -m 'not browser'` | Passed; 372 tests before the final concurrent-revocation regression addition; 32 browser cases excluded for their own gate |
| `.venv/bin/pytest -q tests/test_security.py` | Passed; all 26 tests including the final concurrent-revocation regression |
| `.venv/bin/python scripts/check_postgres.py`; `.venv/bin/python scripts/check_restore.py` | Not run locally; disposable PostgreSQL is provided by hosted CI |
| `npm run build` | Passed |
| `.venv/bin/pytest -q -m browser` | Not run locally; browser installation unavailable after the previously recorded download failure; hosted CI is required |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable` | Passed; no findings |
| `npm audit --audit-level=moderate`; `npm run secrets` | Passed; no findings |
| `uv lock --check`; `npm ci` | Passed; no dependency upgrades |
| `PYTHONPATH=. .venv-legacy/bin/pytest -q` (root) | Passed; 53 legacy tests |
| `LANDWOLF_DATABASE_URL=sqlite:////tmp/landwolf-source-audit/verify.db .venv/bin/python -m landwolf.cli sync` | Passed; all eight implemented listing adapters ready in disposable SQLite |
| `git diff --check`; `git diff --cached --check`; `git status --short` (root) | Passed; reviewed intended files and exact publication tree |

The source audit retrieved MN 4, AR 0, TX 31, USDA 19, Treasury 19, IRS 1, AK 170
and MI 28 records. AR's empty inventory was valid. This does not inspect production
source-state rows. Public research adapters were not changed and research checks
were not repeated; the previously observed FEMA HTTP 502 remains a separate limit.

## Resolved failures and verification limits

An initial lint run identified a loop closure and an overlong status line in the
new hosted check. Both were corrected and formatting/lint passed afterward.
Diff review caught and corrected a broad version substitution in package-lock
before publication; no third-party dependency changed. Existing test-client
deprecation warnings remain; they do not fail tests. Browser/PostgreSQL gates
subsequently passed in hosted CI. Physical devices and a year of actual
elapsed time are not tested; expiry is asserted directly and inactivity simulated.

## Hosted checks and deployment

Final candidate `44b4b77d382ec6510b19347a6ee8ab7156c4b3e4` passed
[application CI 37268825471](https://github.com/lupu-spec/Landwolf/actions/runs/37268825471):
all format/lint/type commands above, 373 backend tests, 9 frontend tests,
`.venv/bin/python scripts/check_postgres.py`, `.venv/bin/python scripts/check_restore.py`
(exact row digests across 21 tables), `npm run build`, all 32 browser journeys,
package/build checks, every configured security scanner, and diff integrity.
The final browser suite includes actual Chromium/WebKit restart/cache/logout tests.
Separate [legacy tests](https://github.com/lupu-spec/Landwolf/actions/runs/37268825424)
and [static release preflight](https://github.com/lupu-spec/Landwolf/actions/runs/37268825465)
also passed. Automated PR review completed without findings.

PR #19 merged as `16b3c5818a5a095b1194fddf0abd46a82c1fb67c`.
Render deployment `dep-db1jj97avr4c73c850vg` became live at
2026-10-05 05:47:01 UTC on the existing production service. Pre-deploy logs
confirmed schema 8, retained accounts/sessions/listings, and successful startup.
No warning/error logs were returned from 05:46:12 through 05:47:34 UTC.

**Passed:** `.venv/bin/python scripts/check_hosted_staging.py --environment production`
in [hosted run 37269249419](https://github.com/lupu-spec/Landwolf/actions/runs/37269249419).
The check confirmed exact v0.4.4/commit identity, HTTPS/database health, production
payments enabled, mail disabled, www redirection, guest authentication, and four
Chromium/WebKit customer journeys at mobile and desktop widths. Unpaid searches
still return 402; coverage endpoints still return 403 for customers.

Both Chromium and WebKit then signed in using real persistent browser profiles,
verified the Secure/HttpOnly/SameSite cookie and >364-day expiration, cleared
JavaScript storage/cache storage, closed the browser process, and reopened the
profile without injecting storage state. The account remained signed in. Chromium
also explicitly cleared its HTTP cache through `Network.clearBrowserCache`.
After deliberate logout, another restart remained signed out in both engines.
The isolated browser suite separately verifies that deleting cookies stays signed
out. No live owner/subscriber was impersonated, mail sent, or payment made; one
disposable non-cohort account was retained. Staging runtime remains v0.4.1.
