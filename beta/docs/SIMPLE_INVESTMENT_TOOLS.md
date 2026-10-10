# Simple investment tools — v0.12.0

The production baseline is branch commit
`5b2b6df7cef1a7d8df254639c05c55d9acd87dbc`, running v0.11.1 at
`a8e66152e753ccdd3fa96821bc32f6c944e8d25f`. This release changes the browser
workflow, not the calculation API, formulas, schema, authentication or billing.

## Behavior

The deal model starts with four numeric inputs: purchase/bid price, expected sale
price, repairs/improvements and title/closing costs. Advanced is collapsed by
default and retains resale/repair bounds, percentages, lien reserve, holding,
financing, selling/auction fees, investment targets and reproducibility seed.
Closing it never removes those values from the request. A visible range summary
and the existing zero-cost warning/required acknowledgement remain outside it.
Missing or invalid figures never silently become valid assumptions.

Initial resale bounds remain the owner's hypothetical bid × 0.95/1.00/1.20.
Editing expected sale makes it the anchor for untouched bounds; edited Advanced
bounds stay fixed. Repair bounds follow the user's budget until edited individually.
A fixed repair budget is a user assumption, not an inferred statistical estimate.
Native numeric validation and range-order errors reveal Advanced when needed.
Per-property session drafts retain overrides across handoffs and clear on logout.
Romulus and Remus's reviewed guide explains the new controls.

The research budget check shows known additional costs and optional net exit
proceeds first. Acquisition overrides, unresolved work and stress assumptions
move into a collapsed Advanced section without changing saved research or math.

## Verification record

| Command (from beta unless noted) | Local result |
| --- | --- |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | **Passed**, exit 0 |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | **Passed**, exit 0 |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | **Passed**, exit 0 |
| `npm run test:unit` | **Passed**, exit 0, 16 tests |
| `.venv/bin/pytest -q -m 'not browser'` | **Passed**, exit 0, 536 tests |
| `npm run build` | **Passed**, exit 0 |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | **Passed**, exit 0, runtime/logo assets packaged |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable` | **Passed**, exit 0, no findings |
| `npm audit --audit-level=moderate`; `npm run secrets` | **Passed**, exit 0, no findings |
| `uv lock --check` | **Passed**, exit 0; only the application version changed |
| Root `git diff --check`; `git status --short` | **Passed**, exit 0, all changes reviewed |

Formatters `.venv/bin/ruff format` on the edited test/script files and
`npm run format` also exited 0 before the checks. Python/JavaScript dependencies
were not changed. A before/after HTML parser comparison confirmed all 21 model
form inputs (20 numeric plus acknowledgement) retain identical input attributes.

**Passed hosted:** root `PYTHONPATH=. pytest -q`, 53 legacy tests, exit 0 in
[38049824216](https://github.com/lupu-spec/Landwolf/actions/runs/38049824216).
Root `PYTHONPATH=. pytest -q tests/unit/test_deployment_preflight.py` passed in
[38049824194](https://github.com/lupu-spec/Landwolf/actions/runs/38049824194).
The workflow's deploy-only legacy environment jobs are intentionally skipped
on PR events, rather than claimed as passed.

**Failed locally, environment limitation:**
`.venv/bin/pytest -q -m browser tests/test_investment_browser.py` could not launch
Chromium/WebKit: their local executables are absent. No browser case ran.
`PYTHONPATH=. pytest -q` could not start: the separate legacy pytest is unavailable.
Hosted CI must cover both before promotion. Disposable PostgreSQL/restore and the
full browser suite are not run locally; required hosted gates remain pending.

The new six real browser/API/database journeys cover Chromium and WebKit at
390/820/1440 px: four default fields, automatic ranges, full submitted Advanced
values while closed, required acknowledgement, invalid hidden input/range errors,
manual override preservation, session handoffs and logout reset. Existing scenario
and research workflow tests now explicitly expand Advanced before editing it.
The hosted staging journey verifies four visible deal inputs and real calculations.

Final gate results and observed staging/production deployment identities will be
recorded after execution. No deployment is claimed here yet.

## Independent source availability check

**Failed**, exit 1, 2026-10-10: explicit disposable-database command
`LANDWOLF_DATABASE_URL=sqlite:////tmp/landwolf-simple-investment-sources.db LANDWOLF_AUTO_SYNC=false .venv/bin/python -m landwolf.cli sync`.
Arkansas COSL returned HTTP 500 from its official `/Home/Contents` endpoint.
Seven other implemented feeds were ready: Minnesota 4, Texas 29, USDA 19,
Treasury 21, IRS 1, Alaska 170, Michigan 28 raw snapshot records. This check
never touched production data or snapshots. No source/parser change is part of
this calculator release. The publisher outage remains a separate limitation.

## Retained and resolved candidate failure

The first full hosted gate run
[38049824189](https://github.com/lupu-spec/Landwolf/actions/runs/38049824189)
passed 536 backend and 16 frontend tests, PostgreSQL integration and 32-table
restore. Browser testing returned **Failed**, exit 1: 96 passed and six help-chat
cases still expected the old button wording `Run 10,000 scenarios`. All six new
simple/Advanced journeys passed. The test now requires `Calculate deal` plus
`Expand Advanced` and checks that the new message clears at logout. This changes
only test expectations to the reviewed UI wording; no assertion is removed.
The full final gates must pass before deployment. Package/security steps in that
failed run were skipped, rather than passed. Local package/security checks passed
as recorded above. No application code changed after this browser run.
