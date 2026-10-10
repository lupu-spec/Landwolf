# CRM contact opening and mobile login — v0.9.2

## Changes

- Opening a CRM contact now immediately shows a loading heading and moves focus
  into its detail section. The completed contact stays in view after rendering.
- Edit contact profile and account administration appear before the long facts
  list. Back to contacts restores list focus; failed requests offer a visible retry.
- On signed-out screens below 640 CSS pixels, the extra chat-only dock is hidden.
  One floating chat launcher remains at the bottom right. Signed-in navigation
  and tablet/desktop controls retain their existing behavior.
- No account, billing, authorization, database schema or email-delivery changes.

## Regression coverage

Chromium and WebKit at 390, 768 and 1440 pixels use 31 persisted contacts, open
an off-screen detail, assert focus and viewport visibility without test scrolling,
edit and save a profile, return to the list, and recover from an HTTP 503. Dock
checks cover signed-out and signed-in states, the 639/640 breakpoint, and a short
viewport. Emulation does not claim a physical iPhone keyboard test.

## Verification status

The final combined candidate passed all required gates. Production and staging
now run v0.9.2; both exact-release hosted checks passed.

## Resumed release

The original mobile candidate passed all gates in run 37422754074 (74 browser tests).
While paused, the Treasury parser repair shipped as production v0.9.1. The resumed
v0.9.2 release merges that repair and its regression test; it does not revert newer
production changes. Full combined checks and live promotion evidence follow.

## Local checks after resuming (2026-10-09)

| Command | Result |
| --- | --- |
| `uv lock --check` | Passed (exit 0) |
| `.venv/bin/ruff format --check landwolf tests scripts` | Passed (exit 0) |
| `npm run format:check` | Passed (exit 0) |
| `.venv/bin/ruff check landwolf tests scripts` | Passed (exit 0) |
| `npm run lint` | Passed (exit 0) |
| `.venv/bin/mypy landwolf` | Passed (exit 0) |
| `npm run typecheck` | Passed (exit 0) |
| `npm run test:unit` | Passed (exit 0) |
| `.venv/bin/pytest -q -m 'not browser'` | Passed (exit 0) |
| `npm run build` | Passed (exit 0) |
| `.venv/bin/pytest -q tests/test_crm_mobile_browser.py -x` | Failed: local Chromium executable missing; full hosted browser gate required |
| `.venv/bin/python -m build` | Passed (exit 0) |
| `.venv/bin/python scripts/check_package.py` | Passed (exit 0) |
| `.venv/bin/bandit -r landwolf` | Passed (exit 0) |
| `.venv/bin/pip-audit --local --skip-editable` | Passed (exit 0) |
| `npm audit --audit-level=moderate` | Passed (exit 0) |
| `npm run secrets` | Passed (exit 0) |
| `git diff --check` | Passed (exit 0) |
| `git status --short` | Passed (exit 0) |

Backend: 472 passed. Frontend: 16 passed. Separate root legacy suite: 53 passed.
Locked installation (`uv sync --frozen --dev`, `npm ci`) passed. The first resumed
staging live-smoke run 37884384647 failed because the old ledger still identified
staging as v0.9.0 while it was running the interrupted mobile v0.9.1 candidate.
The release ledger now records the observed deployments; its live-smoke rerun
checks the corrected identities.

## Verified staging deployment

v0.9.2 staging commit `bb56ad94d19cd56714238c51a701e8c3824ca75e`,
Render deployment `dep-db46ss60tbcc73dbpj2g`, live 2026-10-09 04:34:05 UTC.
`/api/version` and `/api/health` returned 200 with exact identity and ok status.
Hosted check run [37884384630](https://github.com/lupu-spec/Landwolf/actions/runs/37884384630)
passed exact identity, HTTPS, environment/payment/mail configuration, four
Chromium/WebKit customer journeys and persistent-session/cache/logout checks.

## Final combined hosted gates

[Run 37884284006](https://github.com/lupu-spec/Landwolf/actions/runs/37884284006)
passed for candidate `bb56ad94d19cd56714238c51a701e8c3824ca75e`: 472 backend,
16 frontend and 74 Chromium/WebKit browser tests, PostgreSQL authentication and
account/research integration, exact backup/restore digests across 29 tables,
format/lint/types, production build, wheel/source package and all security scans.
Separate legacy [run 37884284000](https://github.com/lupu-spec/Landwolf/actions/runs/37884284000)
and preflight [37884283993](https://github.com/lupu-spec/Landwolf/actions/runs/37884283993) passed.

Additional CI commands (all exit 0):

- `.venv/bin/python scripts/check_postgres.py` (disposable CI database)
- `.venv/bin/python scripts/check_restore.py` (disposable CI database)
- `.venv/bin/pytest -q -m browser` (74 passed)
- Root legacy `pytest -q` (53 passed in its separate environment)

The first October 6 mobile candidate failed two browser assertions that expected
focus on the now-hidden phone dock. Assertions were corrected to require focus on
the visible phone launcher; final coverage was retained and all 74 passed. Local
browser execution after resume remained unavailable because browser binaries were
missing. It is not counted as a local pass; hosted execution supplies that evidence.

## Production promotion

[PR #26](https://github.com/lupu-spec/Landwolf/pull/26) merged as
`356b64ad4a6d6694bd764dd0ec0ff0f6ee942774`. Its tree
`6a8adef438d376a6c91a3c58229db9baa1fff80f` exactly matches the tested staging
candidate. Render deployment `dep-db470mrbc2fs73arhgh0` became live at
2026-10-09 04:42:04 UTC. Direct Render-domain `/api/version` and `/api/health`
returned HTTP 200, v0.9.2, the expected production commit, ok health and payments
enabled. Staging returned the expected candidate and payments disabled.

The local environment returned an HTML “Site Unavailable” response for the custom
domain, so its JSON check failed locally. The hosted check targets `landwolf.ai`
and independently verifies that domain; no local custom-domain pass is claimed.

Production hosted [run 37884987232](https://github.com/lupu-spec/Landwolf/actions/runs/37884987232)
passed on `https://landwolf.ai`: exact identity/HTTPS, environment, live billing mode,
disabled mail, authentication, Chromium/WebKit at 390 and 1440 pixels, owner-only
coverage boundary, paywall, logout, persistent cookies, cache clear and browser
restart. It retained one disposable non-cohort synthetic account. Invitation, consent
and due-date transitions were tested in isolated CI, not against customer records.
Command: `.venv/bin/python scripts/check_hosted_staging.py --environment production`
(exit 0). The staging command used `--environment staging` (exit 0).

## Scope and limits

Changed runtime files: `beta/web/crm.ts` and `beta/web/styles.css`, release metadata
and the corresponding browser tests/workflow evidence. Related CRM, chat and release
documentation and all four illustrated guide editions were updated. Existing owner
permissions, customer profile confirmation, email verification, audit/revision checks,
Treasury repair, database schema 11, billing and account data remain preserved.

Physical iPhone/Safari keyboard testing was not performed; Chromium/WebKit viewport
and focus assertions passed. No claim is made that every device or future upstream
source will work. Real password-reset mail remains disabled until a sender is
configured. This release does not enable outbound email or change live billing.
