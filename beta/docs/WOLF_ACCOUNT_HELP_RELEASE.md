# Romulus and Remus account help — v0.9.0 candidate

This adds customer self-service to the unpublished CRM owner-administration
candidate on `codex/crm-account-administration`, following `ed39e1f`. Version 0.9.0
has not been deployed; this extension remains part of that candidate. Observed
checks below ran on 2026-10-06 UTC (October 5 in America/Chicago).

## Behavior and changed files

- `landwolf/account_profile.py` and `landwolf/crm.py`: authenticated, session-bound
  profile reads/updates and password-reset requests. Users can edit their profile
  fields and marketing preference, but cannot supply another account/contact ID,
  change login email, edit owner controls, or delete a record. Writes use origin,
  CSRF, validation, rate limits, revision checks and transactional CRM activity.
- `web/wolf-account.ts`, `web/wolf-assistant.ts`, `web/help-guide.ts`, `web/app.ts`
  and `web/styles.css`: natural-language account topics, inline forms, a change
  summary and explicit save, reset requests, responsive controls and privacy
  clearing. Conversation text does not become an API mutation. Profile values are
  never persisted to browser storage; stale asynchronous responses are ignored.
- `tests/test_account_profile.py`, `tests/help-guide.test.mjs`,
  `tests/test_wolf_account_browser.py` and `scripts/check_postgres.py`: regression
  coverage for ownership, prohibited fields/deletion, validation, consent, stale
  revisions, rollback, reset mailbox proof, sign-out and real browser journeys.
- `docs/L91_LLC_CRM.md`, the release reports and verification ledger document the
  customer workflow and its boundaries.

The existing recovery flow sends a single-use, 30-minute token to the stored
account email. No password changes until the emailed token is supplied to the
existing secure reset form; completion revokes sessions. Guests can request help
using their registered email without learning whether an account exists. Signed-in
requests accept no email override. Login email correction remains with the owner
or support. Mail delivery must be configured; this turn sent no real-user mail.
No dependency, schema or paid-service change is introduced by this extension.

## Observed verification

Commands ran from `beta/` unless marked. Every **Passed** command exited 0.

| Command | Result |
| --- | --- |
| `.venv/bin/ruff format landwolf/account_profile.py tests/test_account_profile.py` | **Passed**. |
| `.venv/bin/ruff format landwolf tests scripts` | **Passed**. |
| `npm run format` | **Passed**. |
| `.venv/bin/ruff format --check landwolf tests scripts` | **Passed**; 78 files. |
| `npm run format:check` | **Passed**. |
| `.venv/bin/ruff check landwolf tests scripts` | **Passed**. |
| `npm run lint` | **Passed**. |
| `.venv/bin/mypy landwolf` | **Passed**; 34 source files. |
| `npm run typecheck` | **Passed** after fixing a potentially missing form-control access; initial run failed with TS2532, exit 2. |
| `npm run test:unit` | **Passed**; 16 tests, including account intent and no-deletion routes. |
| `.venv/bin/pytest -q tests/test_account_profile.py tests/test_recovery.py` | **Passed**; 32 tests. |
| `.venv/bin/pytest -q -m 'not browser'` | **Passed**; 468 passed, 68 browser cases deselected, 2 dependency deprecation warnings, 94.67 seconds. |
| `PYTHONPATH=. /workspace/scratch/051463328da8/Landwolf/.venv-legacy/bin/pytest -q` (repository root) | **Passed**; 53 tests. |
| `npm run build` | **Passed**. |
| `.venv/bin/pytest -q tests/test_wolf_account_browser.py -x` | **Failed**, exit 1: Chromium executable missing; the first browser could not launch. No new browser journey completed. |
| `.venv/bin/python -m build` | **Passed**; source distribution and wheel include the implementation. |
| `.venv/bin/python scripts/check_package.py` | **Passed**. |
| `.venv/bin/bandit -r landwolf` | **Passed**; no findings. |
| `.venv/bin/pip-audit --local --skip-editable` | **Passed**; no known vulnerabilities. |
| `npm audit --audit-level=moderate` | **Passed**; 0 vulnerabilities. |
| `npm run secrets` | **Passed**. |
| `LANDWOLF_DATABASE_URL=sqlite:////tmp/l91-crm-admin-source-check.db .venv/bin/python -m landwolf.cli sync` | **Passed**; dedicated local database; eight automated feeds returned ready records. |
| `git diff --check` and `git status --short` (repository root) | **Passed**; intended candidate files only. |

The earlier candidate's browser installer had failed on truncated/non-ZIP
downloads. It was not repeatedly retried here. The new browser suite contains six
Chromium/WebKit journeys across 390, 768 and 1440 pixels, covering guest recovery
failure, own-profile review/save, unchanged data before confirmation, mail-disabled
behavior, deletion refusal, responsive overflow and sign-out clearing. These
assertions remain **unverified** until browsers are available. API tests use a
synthetic mail transport to prove mailbox-token/reset behavior; real delivery was
not exercised. Existing FastAPI/httpx and npm environment deprecation warnings
remain. No security finding was suppressed and no failing assertion was weakened.

## Not run and release status

- `.venv/bin/pytest -q -m browser`: **Not run** in full locally because browser
  executables are unavailable. Hosted CI must execute all 68 cases.
- `.venv/bin/python scripts/check_postgres.py` and
  `.venv/bin/python scripts/check_restore.py`: **Not run** locally; the designated
  disposable CI PostgreSQL service is required. The self-profile CAS and storage
  checks have been added to the existing PostgreSQL gate.
- Hosted CI, staging/production deployment, live owner/customer browser review
  and real mailbox delivery: **Not run** for this candidate. No live user account
  or existing environment was changed.

GitHub publication remains blocked by the prior automatic approval review,
which requires explicit approval to upload the source to `lupu-spec/Landwolf`.
This turn did not retry the rejected push or publish through another tool. After
approval, publish the branch, complete hosted checks, stage on the existing
isolated Render service, verify version/commit/health and browser journeys, then
promote to existing production and repeat live verification. Preserve the existing
database and mail/billing configuration; record observed deployment IDs and UTC
times in `RELEASES.md`. Until then, the live application remains unchanged.
