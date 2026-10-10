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

**Passed locally:** formatting, lint and type checks for Python/TypeScript;
`npm run test:unit` (16 invariants); `npm run build`.

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
