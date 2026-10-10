# First-login property map repair

Release v0.10.2, live in staging and production October 10, 2026 UTC.

## Confirmed cause

A read-only query of the live v0.10.1 production inventory found 92 active,
current-sale search matches, 30 with source coordinates. Default price sorting
put 11 Michigan records and one USDA record without coordinates on the first
12-item page. The browser passed only that page to the map: zero map locations
despite 30 elsewhere in the filtered inventory. No source repair or invented
coordinates is appropriate for this failure.

## Repair

`/api/search` returns a compact, independently bounded map selection using the
identical active-sale and search predicates, before list pagination. The list
retains its 12-item pages and original sorting. Map records include only ID,
tract, price and source coordinates, capped at 1,000 with total and limit metadata.
The map displays the cap when reached, and otherwise shows mapped and unlocated
counts. Records without coordinates remain accessible in the list.

The browser clears old pins during search and frames results after the map has a
visible, nonzero size. A ResizeObserver handles the initial hidden mobile list
layout and later map/split transitions. Pins remain clickable, including grouped
locations. Sign-out clears map records. No migration, billing, access, credential,
dependency, source allowlist, snapshot or quarantine change is included.

Changes: `landwolf/main.py`, `web/app.ts`, map explanatory copy in `web/index.html`
and `web/help-guide.ts`; API/browser/PostgreSQL regressions; five version metadata
files. The regressions reproduce 12 unlocated first-page listings with located
records beyond that page, including Chromium/WebKit at 390, 820 and 1440 pixels,
first registration, fresh login, session reload, pagination and clickable markers.

## Verification status

Local commands **Passed**, exit 0, from `beta/`:

- `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check`.
- `.venv/bin/ruff check landwolf tests scripts`; `npm run lint`.
- `.venv/bin/mypy landwolf`; `npm run typecheck`.
- `npm run test:unit` — 16 tests.
- `.venv/bin/pytest -q tests/test_search.py tests/test_version.py` — 16 tests.
- `.venv/bin/pytest -q -m 'not browser'` — 512 passed, 84 browser cases deselected.
- `npm run build`; `.venv/bin/python -m build`;
  `.venv/bin/python scripts/check_package.py`.
- `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable`;
  `npm audit --audit-level=moderate`; `npm run secrets`; `uv lock --check`.
- `git diff --check`; `git status --short`.

Final hosted release gates and production verification passed. Local browser installation
failed because downloaded archives were empty/truncated; hosted CI will supply
the required browser and disposable PostgreSQL/restore checks. The Render SQL
connector cannot access the private database because its external allowlist is
empty; inventory was read through the existing authenticated Render service shell
without changing networking. An initial new test omitted the required JSON body
on logout; it was corrected to the established API contract.

**Failed, unrelated:**
`LANDWOLF_DATABASE_URL=sqlite:////tmp/landwolf-map-release-source-check.db LANDWOLF_AUTO_SYNC=false .venv/bin/python -m landwolf.cli sync`
exited 1 because Arkansas COSL returned HTTP 500. The other seven implemented
listing adapters were ready (MN 4, TX 30, USDA 19, Treasury 21, IRS 1, AK 170,
MI 28). This disposable source check did not alter production data.

**Not run locally:** Chromium/WebKit tests and PostgreSQL/restore. Browser
installation `.venv/bin/playwright install chromium webkit` exited 1 on truncated
download archives, and no disposable local PostgreSQL server is available.
Two existing Starlette deprecation warnings remain. Physical devices were not
tested. Before promotion, the existing production Render Recovery page showed
an enabled Restore database control and a three-day recovery window; no recovery
or networking setting was changed.

## Observed staging deployments

| Runtime commit | Render deployment | Live UTC |
| --- | --- | --- |
| `bc1237f79a335a34dce133c502666f5157ce8540` | `dep-db4rtdflk1mc73fqbuig` | 2026-10-10 04:28:34 |
| `df7854b8a3f125c7b4c5e6ed7c8736fbf28ae881` | `dep-db4rttijnfac738ail40` | 2026-10-10 04:29:30 |
| `e10111c5c9030bb478c2175923fcede22dcbd640` | `dep-db4ru71rn11c73d1otp0` | 2026-10-10 04:30:22 |

The final two revisions change only browser test setup and hosted verification,
not runtime code. All three have the same v0.10.2 application. The final candidate
tree is `4e4ae4caedd0ec56107a726afabd8effb58066b1`; this is the promotion baseline.
PR [#29](https://github.com/lupu-spec/Landwolf/pull/29) contains the repair.

**Passed:** final exact-release staging verification,
`.venv/bin/python scripts/check_hosted_staging.py --environment staging`,
[run 38024233210](https://github.com/lupu-spec/Landwolf/actions/runs/38024233210),
at 04:31:53 UTC. Chromium and WebKit at 390/1440 pixels each verified the live map
inventory independently of list page size and a pin intersecting the visible map.
HTTPS, version/commit, environment, expected mail/payment mode, four customer
journeys, live research response, CSRF/privacy boundaries and persistent-session
cache-clear/browser-restart/logout checks also passed.

**Passed:** final full candidate gates,
[run 38024235473](https://github.com/lupu-spec/Landwolf/actions/runs/38024235473).
In addition to the format/lint/types/unit/build/package/security commands listed
above, hosted CI ran `.venv/bin/python scripts/check_postgres.py` and
`.venv/bin/python scripts/check_restore.py` against disposable `landwolf_ci`:
JSON/null map filtering and pagination independence passed, and all 29 restored
tables matched exact row digests. `.venv/bin/pytest -q -m browser` passed 84 tests
in 378 seconds; backend tests passed 512 and frontend tests passed 16. This includes
all six new phone/tablet/desktop first-login map regression journeys. Legacy
`PYTHONPATH=. pytest -q` passed 53 tests in
[run 38024235472](https://github.com/lupu-spec/Landwolf/actions/runs/38024235472).
Release preflight passed. The staging desktop screenshot visibly showed 30 mapped
locations alongside the unchanged unlocated first list page.

PR #29 merged as `255fd1d9b8969e6c1c352188afca8e8d1669dd56`; its tree exactly
matches the final staged and tested candidate. Render marked production deployment
`dep-db4s35nlot8c73cqeh3g` live at 2026-10-10 04:40:48 UTC. The direct browser in
this workspace cannot open the custom domain (Site Unavailable); this is a runner
limitation. Public-domain verification uses the hosted release workflow, with
additional direct HTTP checks against the production Render origin.

**Passed:** `.venv/bin/python scripts/check_hosted_staging.py --environment production`,
[run 38024845794](https://github.com/lupu-spec/Landwolf/actions/runs/38024845794),
against the exact production merge commit. This verified public HTTPS, identity,
health, enabled payments/mail, four Chromium/WebKit phone/desktop login/paywall/
privacy/logout journeys, and cookie/cache-clear/browser-restart/logout behavior.
The production smoke account has no paid entitlement and appropriately cannot
search; map functionality with live listing data was verified in staging, and the
identical tree was promoted. No owner credentials or access grants were created
to bypass that boundary.

Direct production-origin HTTP checks observed v0.10.2 and exact commit,
`status=ok`, `payments_enabled=true`, `email_delivery_enabled=true`, and anonymous
`POST /api/search` returning 401. Final documentation-only `npm run secrets` and
`git diff --check` passed; the deployment ledger preserves all observed revisions.
