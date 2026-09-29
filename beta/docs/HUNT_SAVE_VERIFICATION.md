# LandWolf Hunt save repair — verification record

## Release

Staging beta only. Runtime v0.4.0-beta.5, commit `af6fbcd8beec4e56e75c527ca27a7d3cf61fb82e`.
Render deployment `dep-dathb62d0e5s73c3uq90` was observed **live** at 2026-09-29 01:35:10 UTC.
PR #8 merged to `codex/landwolf-premium-staging` after release gates passed.
Production remains on commit `c5a5c6d6350441fadafc2c4625c3c7d279d0c6a4`, deployment `dep-daspn8p7lnhs73a8mqk0`.
No production deployment, database reset, schema change, payment change, or dependency upgrade was performed.

## Diagnosis and change

Healthy pre-repair API requests saved successfully in all five acreage bands and survived fresh login.
Fault injection reproduced a distinct real defect: listing validation or matching-storage errors could roll back a new Hunt because matching ran before the save committed.

Preferences now commit before the independent matching transaction. Real write errors remain errors; a matching failure returns a saved Hunt ID with an explicit unavailable status, not a claim of no matching properties.
The page checks the returned ID against the authenticated saved-Hunt list before displaying confirmation. Matching retries are separate, save feedback stays visible, and duplicate/stale responses are guarded.

Main runtime files: `beta/landwolf/main.py`, `beta/web/app.ts`, release version metadata.
Tests: `beta/tests/test_hunt_save.py`, `beta/tests/test_browser.py`, `beta/scripts/check_postgres.py`, isolated live diagnostic scripts.

## Passed: required hosted release commands

Evidence: beta gate run `36507987782`, job `109213640668`; root tests `36507987796`; static release preflight `36507987859`.
Each command below completed successfully after the runtime repair. Python 3.12, Node 24 and locked dependencies were used.

| Command (from beta unless stated otherwise) | Result |
| --- | --- |
| `uv sync --frozen --dev` | Passed |
| `npm ci` | Passed |
| `.venv/bin/playwright install --with-deps chromium webkit` | Passed |
| `.venv/bin/ruff format --check landwolf tests scripts` | Passed |
| `npm run format:check` | Passed |
| `.venv/bin/ruff check landwolf tests scripts` | Passed |
| `npm run lint` | Passed |
| `.venv/bin/mypy landwolf` | Passed |
| `npm run typecheck` | Passed |
| `npm run test:unit` | Passed |
| `.venv/bin/pytest -q -m 'not browser'` | Passed |
| `.venv/bin/python scripts/check_postgres.py` (disposable PostgreSQL 18) | Passed |
| `.venv/bin/python scripts/check_restore.py` (disposable PostgreSQL 18) | Passed |
| `npm run build` | Passed |
| `.venv/bin/pytest -q -m browser` | Passed |
| `.venv/bin/python -m build` | Passed |
| `.venv/bin/python scripts/check_package.py` | Passed |
| `.venv/bin/bandit -r landwolf` | Passed |
| `.venv/bin/pip-audit --local --skip-editable` | Passed |
| `npm audit --audit-level=moderate` | Passed |
| `npm run secrets` | Passed |
| `git diff --check` | Passed |
| `git status --short` | Passed |
| Root environment: `PYTHONPATH=. pytest -q` | Passed |

Focused Hunt suite: 11 tests passed in the locked source-application job `36507710101`.
Database regressions verify malformed-listing and SQLAlchemy failures preserve Hunt rows but roll back incomplete matches; actual Hunt insert failures return 503 without falsely reporting a save. Active-Hunt limits remain enforced.
Browser regressions cover Chromium/WebKit at 390 and 1280 pixels, matching failure/retry, real saved-ID retrieval after reload, failed-write form preservation, and repeated-submit protection.

## Live verification

**Passed:** final diagnostic run `36508680217`, job `109215777574`, completed 2026-09-29 at approximately 01:37:34 UTC. Downloaded artifact `11008246598` was inspected.

- HTTPS `/api/version`: 200, v0.4.0-beta.5, exact runtime commit `af6fbcd8beec4e56e75c527ca27a7d3cf61fb82e`.
- HTTPS `/api/health`: 200, status `ok`, payments disabled.
- All five acreage bands: POST 201, authenticated GET read-back 200 with exact saved IDs, matching 200 and cleanup 200.
- Default Hunt edit: PATCH 200, renamed value persisted after a fresh login with a new cookie jar.
- Live Chromium and WebKit, each at 390 pixels: real UI create 201, same ID after reload, edit 200, edited name retained after another reload, zero page errors.
- Both browsers displayed: “Hunt saved to your account. Find it in Your saved Hunts below.”
- Zero test Hunts remained after cleanup. The inspected WebKit screenshot shows the saved edited Hunt and beta.5 footer.

Commands: `python beta/scripts/check_hunt_save.py` and `beta/.venv/bin/python beta/scripts/check_hunt_save_browser.py` both exited 0. The final diagnostic-only readiness adjustment is on repair-branch commit `96096d7d7570a1330b67d61d8af622646f35420b`; it does not change the deployed runtime.
The unauthenticated web reader could not open the health URLs, and the separate content reader omitted their bodies. Those reader attempts are not counted as verification; the successful HTTPS diagnostic responses above provide the evidence.

## Failures and limits retained

The original fault-injection tests failed before the fix, as expected; their repaired regressions passed.
Early live probes on beta.4 intermittently timed out during startup/navigation or edit interaction. They are not counted as complete passes. The final save probe waits for session initialization before interaction; navigation during unfinished login is outside that probe's coverage.
An attempted additional delayed-session regression workflow was blocked and did not run or change runtime code.
The pre-existing legacy `.github/workflows/release.yml` remains invalid and failed separately; the beta, root-test and static-preflight gates above passed. No gate was disabled or weakened.
Physical iPhone testing, a complete accessibility audit, and fresh public-source synchronization were not run. Adapters were not changed. The live tests use isolated QA accounts and delete only their own Hunts; disposable QA accounts remain because no account-deletion API is available. No credentials are logged.

## Evidence locations

- PR: https://github.com/lupu-spec/Landwolf/pull/8
- Beta release gates: https://github.com/lupu-spec/Landwolf/actions/runs/36507987782
- Final live diagnostic: https://github.com/lupu-spec/Landwolf/actions/runs/36508680217
- Staging: https://landwolf-premium-staging.onrender.com/
