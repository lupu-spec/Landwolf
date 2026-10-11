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
These local gaps are covered by the completed hosted gates below. Disposable
PostgreSQL/restore and the full browser suite were not run locally.

The new six real browser/API/database journeys cover Chromium and WebKit at
390/820/1440 px: four default fields, automatic ranges, full submitted Advanced
values while closed, required acknowledgement, invalid hidden input/range errors,
manual override preservation, session handoffs and logout reset. Existing scenario
and research workflow tests now explicitly expand Advanced before editing it.
The hosted staging journey verifies four visible deal inputs and real calculations.

The final gate results and observed deployment identities are recorded below.

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


## Final candidate gates

Candidate `e062b5386d8a9d672af462594c0b29d524a3c638` passed the full
[hosted gate 38050725379](https://github.com/lupu-spec/Landwolf/actions/runs/38050725379).
Its application code matches the first browser-tested candidate; later commits
change only the verification report and two browser-test files. The new viewport
assertion verifies all four basic inputs are in view at every tested size.

| Command | Hosted result |
| --- | --- |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | **Passed**, exit 0 |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | **Passed**, exit 0 |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | **Passed**, exit 0 |
| `npm run test:unit` | **Passed**, exit 0, 16 tests |
| `.venv/bin/pytest -q -m 'not browser'` | **Passed**, exit 0, 536 tests |
| `.venv/bin/python scripts/check_postgres.py` | **Passed**, exit 0, disposable CI database only |
| `.venv/bin/python scripts/check_restore.py` | **Passed**, exit 0, exact row digests across 32 tables |
| `npm run build`; `.venv/bin/pytest -q -m browser` | **Passed**, exit 0, 102 tests including six basic/Advanced responsive journeys |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | **Passed**, exit 0 |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable` | **Passed**, exit 0 |
| `npm audit --audit-level=moderate`; `npm run secrets` | **Passed**, exit 0 |
| Root `git diff --check`; `git status --short` | **Passed**, exit 0, reviewed |
| Root `PYTHONPATH=. pytest -q` in the separate legacy environment | **Passed**, exit 0, 53 tests in [38050725322](https://github.com/lupu-spec/Landwolf/actions/runs/38050725322) |
| Root `PYTHONPATH=. pytest -q tests/unit/test_deployment_preflight.py` | **Passed**, exit 0 in [38050725327](https://github.com/lupu-spec/Landwolf/actions/runs/38050725327); deployment-only jobs skipped by design on PR events |

The earlier wording-corrected candidate also passed all gates in 38050654411.
The initial six obsolete label failures are resolved, with no test skipped or
assertion removed. Verified screenshots show the four-field basic form, collapsed
Advanced, and readable expanded controls without horizontal overflow. The
Chromium/WebKit viewport checks cover 390/820/1440 px; physical phone/iPad testing
and a complete accessibility audit were **Not run**.

## Files changed

- `web/index.html`, `web/app.ts`, `web/styles.css`: four basic numeric fields,
  Advanced controls, range tracking, hidden-input validation and bounded drafts.
- `web/decision-workspace.ts`: basic research budget costs/proceeds and Advanced
  acquisition, uncertainty and stress controls; existing saved values retained.
- `web/help-guide.ts`: reviewed Romulus/Remus instructions.
- `tests/test_investment_browser.py`, `tests/test_browser.py`,
  `tests/test_decision_browser.py`, `tests/test_wolf_assistant_browser.py` and
  `scripts/check_hosted_staging.py`: responsive API and hosted regression coverage.
- `landwolf/version.py`, `pyproject.toml`, `uv.lock`, `package.json` and
  `package-lock.json`: application version 0.12.0 only, no dependency changes.
- `README.md`, `docs/MODEL.md`, `docs/VERIFICATION.md`, this report and root
  `RELEASES.md`: behavior, command evidence and deployment records.


## Staging observation

Render deployment `dep-db52qe2d0e5s73e0hblg` reported **live** at
2026-10-10 12:20:08 UTC on the existing staging service and its separate database.
`/api/version` returned v0.12.0, staging and exact candidate
`e062b5386d8a9d672af462594c0b29d524a3c638` in the hosted check.

**Passed**, exit 0: `.venv/bin/python scripts/check_hosted_staging.py --environment staging`
with the exact expected commit, in
[38051509798](https://github.com/lupu-spec/Landwolf/actions/runs/38051509798).
All four Chromium/WebKit 390/1440 px journeys verified the four default numeric
inputs, real research budget/model results, mapped inventory, property handoffs,
owner-only coverage and privacy. Persistent-profile restart, cache clearing and
logout checks passed in both browsers. Live public research returned ready.
Billing/email/trial flags remain disabled on staging. One recognized synthetic
smoke account is retained; no real payment or user credentials were used.

PR #34 merged as `7b06ded06beca5bb4b54f3dcbaf83158e072c74f`; its Git tree
matches the exact tested/staged candidate tree. Production deployment and verification are recorded below.


## Production observation

Render deployment `dep-db52sd7avr4c73f8u6l0` reported **live** at
2026-10-10 12:24:06 UTC on the existing production service/database. Direct HTTPS
origin checks exited 0: `/api/version` returned v0.12.0, production and exact
merge `7b06ded06beca5bb4b54f3dcbaf83158e072c74f`; `/api/health` returned ok with
live payments enabled; anonymous `/api/session` retained payments, email delivery
and feedback-trial flags true. The HTML parser verified the served model has
exactly four basic numeric fields and Advanced without an open attribute.
These direct checks used a bounded Python urllib/HTMLParser script with assertions.

**Passed**, exit 0: `.venv/bin/python scripts/check_hosted_staging.py --environment production`
with the exact expected commit in
[38051761573](https://github.com/lupu-spec/Landwolf/actions/runs/38051761573).
The canonical domain returned the exact live release; all four Chromium/WebKit
mobile/desktop login/paywall/privacy/logout journeys passed, plus actual profile
restart/cache/session persistence. One recognized non-entitled smoke account is
retained. Production calculator access remains gated; the real calculation and
research journeys run on the identical staged tree, without a real payment.

No environment values, Stripe configuration, credentials, network permissions,
database migrations or data-source code were changed. The billing/CRM trial and
complimentary architecture is retained. No real subscription, settlement or
physical-device test was run for this UI release. The independent Arkansas
publisher outage remains documented separately above. This documentation update
records observations; it does not redeploy either service or redefine its runtime.
