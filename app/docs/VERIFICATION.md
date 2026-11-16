# LandWolf verification

## v0.24.0 — accessibility improvements deployed and verified

- Candidate: `99aa3d68a74dd4370ce398478c1c34dd7962d938`; [PR #54](https://github.com/lupu-spec/Landwolf/pull/54).
- Staging: `f904d5e34a7a9b1a8b82e194403a8392a54e9294`, Render `dep-dbn05kjrjlhs73ckrm90`, live 2026-11-06 16:41:03 UTC.
- Production: `18b53c81a3a3a662b9dbd7eb1681dbd3b9ba1718`, Render `dep-dbn09915efls738ohvug`, live 2026-11-06 16:48:47 UTC.
- All three commits have the identical complete tree `748101bc119db865df4adfa610155342454c0662`. Runtime 0.24.0; schema 18 unchanged.

Corrects visible/accessibility-name mismatches, invalid result-toggle semantics,
unnamed groups, keyboard access to finance tables, map-credit contrast, public
canvas colors, focus hidden by floating controls, and long-account text reflow.
Adds error/help associations, result announcements, reduced-motion scrolling,
map List guidance and the public `/accessibility` statement. Existing native
dialog and focus-return behavior is regression-tested. Authentication, billing,
entitlements, customer data and infrastructure are preserved.

Final application [CI 42247666585](https://github.com/lupu-spec/Landwolf/actions/runs/42247666585)
passed 782 backend/API, 28 frontend and 172 browser cases, separate exact header
comparison, PostgreSQL integration, disposable backup/restore across 49 tables,
format/lint/types, production packaging and security. Factory 42247666690 and
legacy 42247666728 passed. Axe checked 184 isolated fixture states, plus
96 live staging and 64 live production states,
with zero WCAG-tagged violations. Incomplete results remain for human review.
Exact-runtime hosted session/customer and public-page checks exited 0 in both
environments, including mobile/desktop, themes, logout and persistence.

Local Docker WebKit retained a maximum-one-RGB-level difference in an exact dock
image comparison: the earlier full command had 171 passed/1 failed; the final
focused command had 9 passed/1 failed. Hosted exact header/full-suite gates passed
unchanged. A fresh-render diagnostic produced identical approved/current PNGs;
a longer control was inconclusive after a fixture-loading timeout. No assertions
were relaxed. The PR-triggered hosted workflow 42247666764 failed before deployment
because the expected runtime was not live; no account tests ran in that workflow.
It is not relabeled passed. Explicit post-deployment acceptance exited 0.

Manual screen-reader/physical-device testing, gradient/translucent contrast review,
third-party maps/payment/source documents and entitled production-owner journeys
remain unverified. Owner/admin flows were exercised with isolated fixtures;
hosted ordinary accounts were denied owner APIs. No legal certification or complete
WCAG conformance is claimed. See `app/docs/ACCESSIBILITY.md` for the manual checklist.
This documentation-only sign-off does not redeploy or relabel the observed runtimes.
The prior 0.23.1 release uses the same schema and is the compatible code rollback
candidate; no database reset or restore was performed.

### Command evidence

Commands are from `app/` unless noted. Final application CI ran the configured
commands in repository order. Passed means exit 0; local failures remain separate.

| Command | Result |
| --- | --- |
| `uv sync --frozen --dev`, `npm ci`, `uv lock --check` | Passed; locked axe dependency installed |
| `.venv/bin/ruff format --check landwolf tests scripts`, `npm run format:check` | Passed |
| `.venv/bin/ruff check landwolf tests scripts`, `npm run lint` | Passed |
| `.venv/bin/mypy landwolf`, `npm run typecheck` | P…60547 tokens truncated…Failed** | Exit 1; disposable GitHub PostgreSQL container unavailable |
| `npm run build` | **Passed** | Exit 0 |
| `.venv/bin/pytest -q -m browser tests/test_source_list_browser.py --maxfail=1` | **Failed** | Exit 1; Chromium executable absent after failed browser download; no UI behavior assertion ran |
| `.venv/bin/python -m build` | **Passed** | Exit 0 |
| `.venv/bin/python scripts/check_package.py` | **Passed** | Exit 0 |
| `.venv/bin/bandit -r landwolf` | **Passed** | Exit 0 |
| `.venv/bin/pip-audit --local --skip-editable` | **Passed** | Exit 0 |
| `npm audit --audit-level=moderate` | **Passed** | Exit 0 |
| `npm run secrets` | **Passed** | Exit 0 |
| `git diff --check` | **Passed** | Exit 0 |
| `git status --short` | **Passed** | Exit 0 |

Additional verification: `PYTHONPATH=. /tmp/landwolf-legacy-venv/bin/pytest -q`
from `archive/legacy/`: **Passed**, 53 tests, isolated requirements environment.
`.venv/bin/python -m compileall -q landwolf ../archive/legacy/app ../archive/legacy/scripts`:
**Passed**. Active Bandit JSON scan: **Passed**, zero issues. Archived Bandit scan:
**Failed** with one low-severity B105 result; reviewed as a placeholder-rejection
comparison, not a deployed credential. `git push -u origin codex/source-health-redesign`:
**Failed**, local Git has no GitHub credential; connector publication is used instead.

`.venv/bin/playwright install chromium webkit`: **Failed**, browser archive was
invalid/truncated. The focused source-list browser command failed at launch.
Full browser suite, disposable PostgreSQL and restore: **Not run to completion**
locally; hosted CI must pass them before any deployment. No tests were skipped or
weakened to ship this change. The first `npm run format` from repository root
failed because package.json is in app/; rerun there passed.

After the final code refactor: formatting, ESLint, Ruff, mypy, all frontend
TypeScript files, frontend/backend unit suites, browser build, wheel/sdist and
package-content checks completed as listed. Runtime/dependency version is 0.14.0.
Python/npm audits and the configured masked secret scan returned zero findings.
Known test-tool warnings concern deprecated Starlette/httpx test-client APIs.

Current guides updated in the repository: README, source docs, owner coverage
guide, DATA_SOURCE_VIEW, AI_CHANGE_GUIDE, and Romulus/Remus owner coverage help.
The stored PDF/HTML manual refresh is separate and must not claim this candidate
is deployed before a live version/commit check.

### Initial hosted candidate: 5551b5e

[Run 38907172062](https://github.com/lupu-spec/Landwolf/actions/runs/38907172062)
passed static checks, 24 frontend, 572 backend/API, disposable PostgreSQL and
restore, 18 focused existing browser journeys and 114 existing full browser
journeys. The four new source-list scenarios failed. Root cause: the Python
Playwright clock API accepts numeric **seconds** and converts them to milliseconds;
the test passed milliseconds and moved the browser thousands of years ahead.
The production source-age implementation correctly rendered the synthetic
records red. The test now passes an explicit UTC datetime and asserts browser
clock alignment before checking unchanged green/yellow/red expectations.
No production threshold or failure assertion was weakened. Packaging/security
were skipped in that hosted job following the failure; their local passes above
remain separate evidence. Production and staging were not deployed.

Screenshot review also found that rem-sized columns could starve the source-name
column at 200% font zoom on narrow phones without causing page-level overflow.
Mobile columns now reserve 28px for the circle and 40% for the timestamp, leaving
a usable source-name column; the timestamp is 12px at default scale. A browser
assertion checks usable name width and overflow at 200% and records a zoom image.
Owner help keywords now include freshness/colors. The four source-list journeys
run first in hosted browser validation so a regression is reported promptly;
all original focused and full suites remain mandatory and unchanged.

The corrected candidate's second hosted run spent 7m32s on cold environment setup
(compared with about 68s initially). The existing browser step took about 13m15s
including focused and full suites. Together with units/build/security this makes
the former 20-minute job budget insufficient for a cold runner. The job budget
is now bounded at 30 minutes; all format/type/unit/database/browser/package/
security checks remain required, with no removed cases, assertions or suites.

### Verified candidate and staging image

[Run 38911250054](https://github.com/lupu-spec/Landwolf/actions/runs/38911250054)
completed successfully at candidate `612b737fa28cef71ad3c16d379fb33fe03f3fa1b`.
All configured gate commands passed: format, lint, mypy, full frontend types,
24 frontend, 572 backend/API, 4 focused source-list, 18 existing focused browser,
118 full browser, disposable PostgreSQL, exact 36-table pg_dump/pg_restore row
digests, browser build, wheel/sdist, required package contents, Bandit, pip-audit,
npm audit, secretlint and diff checks. Archived run 38911250076 passed 53 tests.
The earlier clock-harness failure and the 20-minute cold-runner timeout remain
recorded above; neither was counted as a pass.

Staging Render deployment `dep-db931eeq1p3s739sq6bg` reports live at 14:13:26 UTC
on October 16 with exact candidate commit 612b737. The new release-check script
adds public stylesheet hash and computed-theme verification; it changes only
release verification, not Docker application code. Ruff format/check passed in
the release checkout (94 Python files). Hosted staging acceptance remains pending
until its workflow finishes; production remains on the previous v0.13.1 image.

### Production image and hosted staging acceptance

Staging hosted run 38914439829 completed **Passed**. It checked exact v0.14.0/
612b737, health, public stylesheet SHA-256, computed graphite theme, Chromium/
WebKit at 390/1440px, live mapped inventory, successful actual public research,
CSRF rejection, property/research handoffs, owner-only coverage boundaries,
persistent cookies, cache clear, real browser restart and logout. It retained
one disposable non-cohort staging verification account; it performed no payment.
Live smoke 38914439897 passed then-current identities, HTTPS/logo/fallback and
www redirection. The former Current environments table's v0.13.0 entries were
stale; they were corrected using observed releases, not inferred branch heads.

PR #38 squash-merged as 3679070c575591873d556bab8504c7d55b5635d7. Native GitHub
Git-tree fetch verified its entire tree equals the candidate/staged runtime tree
f4fadb9a2467f0009200fffba4e45bad39509212. Production deployment
dep-db935gajnfac739mv6s0 is **live** at 2026-10-16 14:21:53 UTC. Final hosted
production acceptance is triggered by this observed ledger update and remains
pending until that workflow completes. Auto-deploys remain off; no database
reset, account grant, Stripe configuration edit, subscription or payment was made.

### Final production acceptance and documentation - Passed

[Hosted production run 38915826912](https://github.com/lupu-spec/Landwolf/actions/runs/38915826912),
job 117022905156, completed successfully. The current `scripts/check_hosted_staging.py`
with `--environment production --commit 3679070c575591873d556bab8504c7d55b5635d7`
verified exact version/commit/health, production billing and email modes, deployed
graphite stylesheet SHA-256 and computed CSS, anonymous API protection, four real
Chromium/WebKit 390/1440px login/paywall/logout journeys, private source/finance
boundaries, secure persistent cookies, cache-only clearing, actual browser-profile
restart and logout. It made no payment or account grant. One disposable standard
production smoke account is retained and follows existing smoke-account filtering.

Live smoke run 38915826834 passed exact identities in staging and production,
HTTPS, supplied-logo and fallback-image digests, and www redirection. Subsequent
release-log commits are documentation/verification evidence; automatic deployment
is off and runtime commits remain staging 612b737 / production 3679070.

Three current PDF manuals and two current HTML manuals were replaced successfully
while preserving their identities/version histories. PDF updates were rendered
and visually reviewed with embedded fonts; all original reference-page text was
checked unchanged behind the two current update pages. HTML image sources and
original scripts were checked unchanged. Current instructions cover the graphite
interface, source disclosures, exact age boundaries, local timestamps, loaded-
status refresh behavior, owner restriction and current self-service trial terms.
In-app help and repository guides are updated too.

Remaining limits: physical OS keyboards and real payment conversion/email-inbox
delivery were not exercised. Owner diagnostic interactions ran in isolated CI;
production customer checks verify the owner boundary without impersonating an
owner. No production data-source refresh or provider parser change was requested
or performed. The independent local cloud browser could not reach LandWolf;
GitHub-hosted HTTPS/browser checks supplied the successful live verification.
The configured runtime/security gates passed on the candidate whose full Git tree
exactly equals the production application image. Later documentation-only pushes
can start redundant automatic CI checks; they do not constitute new deployments.

## v0.15.0 complete appearance — candidate verification

Changes: shared light/dark silver/glass tokens across feature surfaces and inputs,
header Auto/Light/Dark selection, browser persistence, pre-paint external bundle,
system/cross-tab updates, print colors, in-app help and appearance documentation.
No provider, account, billing, research calculation or schema runtime was changed.

Commands run from `app/` in the existing locked Python/Node environments:

| Command | Result |
| --- | --- |
| `.venv/bin/ruff format --check landwolf tests scripts` | Passed: 95 files |
| `npm run format` then `npm run format:check` | Passed; formatter diff reviewed |
| `.venv/bin/ruff check landwolf tests scripts` and `npm run lint` | Passed |
| `.venv/bin/mypy landwolf` and `npm run typecheck` | Passed |
| `npm run test:unit` | Passed: 26 tests |
| `uv lock --check` | Passed; only own release metadata changed, no dependencies added |
| `npm run build` | Passed, including the new blocking theme bundle |
| `.venv/bin/python -m build` and `.venv/bin/python scripts/check_package.py` | Passed: wheel/sdist and required appearance assets/tests |
| `.venv/bin/bandit -r landwolf` | Passed: no active-runtime findings |
| `.venv/bin/pip-audit --local --skip-editable` and `npm audit --audit-level=moderate` | Passed: no known vulnerabilities |
| `npm run secrets` | Passed: masked scan |
| `git diff --check` and `git status --short` | Passed; intended changes only |
| `.venv/bin/pytest -q -m browser tests/test_theme_browser.py -x` | Failed locally: missing Chromium executable, before any UI assertion |
| `.venv/bin/playwright install chromium webkit` | Failed: browser archive download/extraction failure |

Full API tests are running. Required real-browser, PostgreSQL and restore gates
remain pending in hosted CI; local browser unavailability is not a pass. The
new focused appearance suite runs before all existing browser suites, followed
by the full browser suite. Nothing is deployed until those gates and staging
acceptance succeed. Early command path errors were corrected; they made no code
or dependency changes. Later release evidence will record actual outcomes.

Local API run completed with 571 passed and one release-metadata mismatch:
`test_distribution_versions_match_runtime` found the pre-existing editable install
still at v0.14.0. `uv sync --frozen --dev` reinstalled only LandWolf v0.15.0 from
this checkout; `pytest -q tests/test_version.py` then passed all 7 tests. No
dependency version or test assertion was changed. Hosted CI installs the same
frozen environment from scratch. Print semantic colors were also reviewed for
dark-mode printing, and appearance tests require normal-text input contrast.

Hosted run 38958375508 passed static/types, all 26/572 unit/API tests,
PostgreSQL and exact restore checks. Its first appearance suite stopped at an
ambiguous test locator: both the dock Feedback button and a hidden pilot button
share `data-nav="feedback"`. Scoped the new test to `#main-nav`; no runtime
change or assertion was removed. Both invalid/blocked-storage cases passed.
The identical locator in the concurrent follow-up run is superseded by this fix.
The final local full API run passed 572 tests; the legacy suite passed 53 with
its required `PYTHONPATH=.` from `archive/legacy/`. Earlier legacy invocations
from the wrong working directory/import path failed and are not counted as passes.

Visual review of the first hosted artifacts caught a real CSS regression: the new
header `backdrop-filter` created a containing block for the fixed mobile dock,
placing it at the header instead of the viewport bottom. Removed that header
filter (the dock and cards retain their own glass surfaces), added an explicit
mobile dock position assertion, and normalized native select painting/chevrons
for WebKit. The focused heading keeps programmatic focus for screen readers
without a decorative ring around the heading. Current screenshots also show the
original mixed white cards have been replaced by graphite feature surfaces.

The mobile header may wrap at large text sizes so the new Appearance selector
and Sign out remain reachable at 200% font zoom. This preserves the existing
source-list zoom/no-horizontal-overflow regression rather than hiding controls.

The corrected navigation journey in run 38959025903 reached Membership and found
its outer section had no shared surface class (its inner plans were themed).
Applied the same `source-panel` container used by Research/Hunt/Feedback, keeping
the all-feature glass-surface assertion intact. This is a presentation change
only; payment controls and runtime decisions are unchanged.

Run 38959882690 passed all eight appearance journeys (81.60s), four source-list
journeys including 200% text zoom (19.57s), and 14 of 18 existing focused journeys.
Four mobile Research cases caught a real regression: the shared appearance
`font: inherit` rule overrode the established 16px decision-input safeguard with
its label's 14.4px size. Removed only that cosmetic font reset; the original
layout/mobile font rules and their 16px assertions are retained. Full browser,
package/security and deployment gates remain pending for the corrected source.

Full candidate run 38961099914 passed 125 of 126 browser cases but failed the
834px WebKit twin-guide journey on an unhandled `ResizeObserver loop completed
with undelivered notifications` error. Existing dock resize callbacks wrote
arrow visibility/layout during resize delivery; map invalidation also mutated
layout from a resize callback. Both updates now coalesce into the next animation
frame. Added real repeated phone/tablet/desktop boundary resizing to the dock
journey and retained the zero-page-error assertions. No errors are suppressed or
filtered. Required gates are being rerun on the corrected source before release.

On corrected source 29d4d465498feb60972c26b6f570aed5dce40105, the local production
package build/check, Bandit, pip-audit, npm audit, masked secret scan and diff/status
checks all completed successfully again. No known dependency vulnerabilities or
active Bandit findings were reported. Hosted focused results observed in the
current run: 8 appearance cases (95.96s), 4 source-list cases (24.45s), and all 18
mobile/dock/chat cases including repeated boundary resizing (138.17s) passed.
Full 126-case browser and final hosted release gates remain pending at this note.

### Corrected v0.15.0 candidate — Passed

[CI run 38963112491](https://github.com/lupu-spec/Landwolf/actions/runs/38963112491),
job 117182843740, completed successfully on immutable source
`29d4d465498feb60972c26b6f570aed5dce40105`, Git tree
`770b1ae8c75c7488d6641dc6b017558413378b0c`. Every configured gate completed:
format/lint/types, 26 frontend unit cases, 572 backend/API cases, PostgreSQL
integration and exact pg_dump/restore digests over 36 tables, 8 focused appearance
cases, 4 source-list cases, 18 existing mobile/dock/chat cases, and the full 126
browser cases (819.19s). Wheel/sdist validation, Bandit, pip-audit, npm audit,
masked secret scanning and diff integrity passed too. Legacy run 38963112547
passed 53 tests separately. No test, assertion, suite or error filter was removed
to obtain the pass. The root command table above applies to these exact gates;
the hosted CI installs the frozen environments and real Chromium/WebKit engines.

Staging deployment dep-db98ukmq1p3s739krerg was triggered for that exact commit;
only an observed live deployment and its subsequent hosted checks establish
release acceptance. The earlier failures are retained as resolved evidence.

### Observed v0.15.0 staging deployment — Live, acceptance pending

Render `dep-db98ukmq1p3s739krerg` finished live at 2026-10-16 20:56:57 UTC with
exact commit 29d4d465498feb60972c26b6f570aed5dce40105. This evidence update records
that immutable runtime in the Current environments table and triggers the hosted
acceptance checker against it. The initial source push carried the previous
runtime ledger; only the corrected ledger's acceptance run establishes v0.15.0.
Production is still the existing v0.14.0 image at this checkpoint.

### Hosted v0.15.0 staging acceptance — Passed

[Hosted staging run 38965980741](https://github.com/lupu-spec/Landwolf/actions/runs/38965980741),
job 117192446069, passed exact version/commit/health, deployed stylesheet hash,
Light/Dark selection and reload persistence, Chromium/WebKit 390/1440px customer
journeys, actual mapped inventory independent of list pagination, live public
research, CSRF rejection, private owner boundaries and real browser-profile
persistence/cache-clear/restart/logout. Live smoke 38965980738 passed current
staging/production identities, HTTPS and branding assets. One disposable standard
non-cohort staging account is retained under existing smoke-account filtering.

PR #39 was squash-merged as 55a35648140ffb3d3dead8c2e09a54d55dfc0e63. Native Git
object lookup proved its complete source tree exactly equals tested candidate
29d4d46: 770b1ae8c75c7488d6641dc6b017558413378b0c. Production deployment
`dep-db990vrbc2fs73eqpo2g` was triggered with that exact merge commit. An observed
live result and production hosted acceptance are still required at this checkpoint.

### Observed v0.15.0 production deployment — Live, acceptance pending

Render `dep-db990vrbc2fs73eqpo2g` finished **live** at 2026-10-16 21:02:02 UTC
with exact squash commit `55a35648140ffb3d3dead8c2e09a54d55dfc0e63`. Its full
Git tree equals the tested/staging tree above. This corrected ledger triggers
production hosted checks using that exact immutable identity. Both service
branches retain auto-deploy off; publishing this evidence does not deploy a new
image. Existing databases, accounts and billing configuration remain in place.

### Final v0.15.0 production acceptance — Passed

[Production hosted run 38966641513](https://github.com/lupu-spec/Landwolf/actions/runs/38966641513),
job 117194632178, completed successfully against exact v0.15.0 production commit
55a35648140ffb3d3dead8c2e09a54d55dfc0e63. It checked identity/health, production
billing and email modes, deployed stylesheet SHA-256, both Light/Dark appearances
and reload persistence, Chromium/WebKit 390/1440px login/paywall/logout, private
coverage/finance boundaries, secure persistent cookies, cache-only clearing and
actual persistent-browser-profile restart/logout. The existing owner/account/
billing gates remain enforced server-side. One disposable standard non-cohort
production verification account is retained under existing smoke filtering; no
payment, subscription or owner grant was created.

Live smoke 38966641453 passed both current runtime identities, HTTPS, logo and
fallback-image hashes, and www redirection. Final candidate screenshots were
visually inspected in dark/light phone Explore, dark desktop Sources and light
tablet chat after the last styling changes. They are internal synthetic-account
QA evidence, not user-facing screenshots or copies of production customer data.

The immutable staging and production images have the exact full Git tree that
passed all gates. Later commits update evidence/guidance only; auto-deploy stays
off. Redundant push-triggered CI on those docs is separate from the verified
runtime release. Physical iOS keyboards, real payment conversion and email inbox
delivery were not run. Owner diagnostics were tested in isolated CI; live customer
checks establish their access boundary without impersonating an owner. No data-
source parser/provider, database schema or payment/trial runtime was changed.

### Current guides and final command record — Passed

The three current PDF manuals (9/16/30 pages) and two current HTML manuals were
replaced successfully in their existing identities/version histories. All five
ordered save results reported `succeeded` and local metadata applied. Current
update pages cover Auto/Light/Dark, browser/system behavior, source disclosures,
account/trial notes and mobile controls; historical reference pictures are labeled
as such. Every original PDF reference page's text and HTML image/script list was
checked retained. The final release-note page was rendered and visually checked
with embedded fonts after changing its status to verified staging/production.
In-app help, README, Appearance and AI change guidance are current.

The exact configured commands and their final verified results are below.
Commands are from `app/` unless stated; PostgreSQL commands used only disposable
CI PostgreSQL, never production. Earlier local failures and their resolution remain
above; unavailable local browser installation was resolved by actual hosted runs.

| Command | Final result |
| --- | --- |
| `uv sync --frozen --dev`; `npm ci`; `.venv/bin/playwright install --with-deps chromium webkit` | Passed in CI |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | Passed |
| `npm run test:unit` | Passed: 26 |
| `.venv/bin/pytest -q -m 'not browser'` | Passed: 572 |
| `.venv/bin/python scripts/check_postgres.py` | Passed |
| `.venv/bin/python scripts/check_restore.py` | Passed: exact digests, 36 tables |
| `npm run build` | Passed |
| `.venv/bin/pytest -q -m browser tests/test_theme_browser.py` | Passed: 8 |
| `.venv/bin/pytest -q -m browser tests/test_source_list_browser.py` | Passed: 4 |
| `.venv/bin/pytest -q -m browser tests/test_mobile_research_browser.py tests/test_dock_browser.py tests/test_wolf_assistant_browser.py` | Passed: 18 |
| `.venv/bin/pytest -q -m browser` | Passed: 126 |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable`; `npm audit --audit-level=moderate` | Passed: no active Bandit findings or known dependency vulnerabilities |
| `npm run secrets` | Passed, masked findings |
| `uv lock --check` | Passed locally, no dependency versions changed |
| `.venv/bin/pytest -q tests/test_version.py` after frozen editable reinstall | Passed locally: 7 |
| `git diff --check`; `git status --short` | Passed, intended changes only |
| `PYTHONPATH=. pytest -q` from the separate `archive/legacy/` environment | Passed: 53 |
| `.venv/bin/python scripts/check_hosted_staging.py --environment staging --commit 29d4d465498feb60972c26b6f570aed5dce40105` | Passed |
| `.venv/bin/python scripts/check_hosted_staging.py --environment production --commit 55a35648140ffb3d3dead8c2e09a54d55dfc0e63` | Passed |
| Live-smoke workflow 38966641453 embedded Python HTTPS/version/asset checks | Passed |

No application deployment follows these documentation-only sign-off commits.
Runtime identities remain staging 29d4d46 / production 55a3564. Larger route/contract
and base-layout consolidation from the repository review remains follow-up work;
this release completed the requested appearance and its necessary regressions.


## Public SEO candidate v0.16.0 — October 18, 2026

PR #41 is separate from unmerged CSS PR #40. Public information is rendered in
HTTP HTML, with explicit public routes, production sitemap/robots, canonical URLs,
unique descriptions, breadcrumbs and visible-content FAQ schema. Staging and API
noindex protections and all authorization/billing/CRM boundaries remain in place.
Three WebP derivatives reduce delivered bundled raster bytes from approximately
4.4 MB to 0.84 MB; supplied originals remain unchanged. See PUBLIC_SEO.md.

Passed locally (exit 0, from app unless noted):

- `uv sync --frozen --dev`, `npm ci`, `uv lock --check`.
- `.venv/bin/ruff format --check landwolf tests scripts`, `npm run format:check`.
- `.venv/bin/ruff check landwolf tests scripts`, `npm run lint`.
- `.venv/bin/mypy landwolf`, `npm run typecheck`.
- `npm run test:unit`: 26 passed.
- `.venv/bin/pytest -q -m 'not browser'`: 584 passed, 132 browser cases deselected;
  two existing test-client deprecation warnings. Final runtime rerun: 102.31 seconds.
- `.venv/bin/pytest -q tests/test_public_pages.py`: 12 passed after moving all
  prebuilt static assets aside; its session fixture ran the real `npm run build`.
- `npm run build`, `.venv/bin/python -m build`,
  `.venv/bin/python scripts/check_package.py`.
- `.venv/bin/bandit -r landwolf`: no findings;
  `.venv/bin/pip-audit --local --skip-editable`: no known vulnerabilities;
  `npm audit --audit-level=moderate`: zero vulnerabilities; `npm run secrets`: no findings.
- `git diff --check` and `git status --short` from the repository root.

Failed / unavailable locally:

- `.venv/bin/playwright install chromium webkit` failed with a truncated Chromium
  download. `.venv/bin/pytest -q -m browser tests/test_public_pages_browser.py -x`
  failed because the Chromium executable was unavailable. This is not a browser pass.
- Full browser, disposable PostgreSQL/restore and legacy environments were not run
  locally; hosted application/legacy CI must supply these required release gates.
- Initial hosted application runs 39156489979 and 39156604200 failed public HTTP
  tests because a clean checkout had no built assets. The new session fixture builds
  real assets before HTTP checks; no assertion or test was removed or skipped.
- A long secure Google sign-in request timed out. The scratch workspace was cleared
  during the wait; changes were restored and saved to the separate PR. No Search
  Console submission or verified-property access is claimed.
- Live HTTPS requests from this local environment returned an intermediary “Site
  Unavailable” HTML page even at HTTP 200. They cannot establish origin status,
  redirects, real 404s or field speed. Hosted acceptance remains required.

Hosted checks, screenshot review and deployment evidence are pending in this entry.
No production/staging deployment, ranking, earned backlink or sub-two-second field
performance is claimed here. Personal bio text is pending the owner’s factual input.
Google's current documentation confirms FAQ rich results were removed May 7, 2026;
the earlier health/government-only guidance was outdated and is corrected in PUBLIC_SEO.md.


### Native public-origin baseline and browser diagnostics

Read-only audit run 39158373200 (2026-10-18 19:21 UTC), isolated from runtime
branches, observed production v0.15.0 at commit
`55a35648140ffb3d3dead8c2e09a54d55dfc0e63`. Canonical HTTPS home and trial terms
returned 200. HTTP/apex and HTTPS/www each returned one permanent 301 directly to
`https://landwolf.ai/`; no redirect-chain change is needed for those origins.
Robots and sitemap returned genuine 404s. One 20-second staging version request
timed out; that is not evidence that staging is down and is not staging acceptance.

Application runs 39156896926, 39157123463 and 39157342595 failed the new WebKit
computed body-color assertion. Chromium passed all three widths. Retained Chromium
metrics showed maximum local load 100.9 ms and maximum CLS 0.000597 across the
captured public pages and home. These are local CI measurements, not field speed.
Artifact 12147925992 shows the public stylesheet loaded and a WebKit screenshot
with the intended RGB(32,35,43) text, despite a pre-capture computed read returning
black. The same exact computed-color expectation now runs after an actual paint;
it has not been removed, masked or given a different expected value. Further
stylesheet, inherited color and screenshot diagnostics remain on failure.

Review also aligned graphite's workspace heading selector with its H2 tag. Its
ARIA level remains 1 in the active signed-in view, and existing typography/layout
rules retain the approved values. A theme journey now checks its exact Light/Dark
text color after login. This changes no navigation or account/billing behavior.

Local browser fallback attempts: Chromium headless-shell download also failed with
a truncated ZIP. WebKit downloaded, but its required OS libraries are unavailable;
`.venv/bin/playwright install-deps webkit` failed with denied setgroups/setuid
operations. Full browser verification therefore remains a hosted gate. No OS
sandbox or browser protection was disabled to obtain a pass.


### Full browser result before final asset/redirect corrections

Run 39157812908: focused public browsers passed all six Chromium/WebKit cases;
all eight theme cases, four source-list cases and 18 mobile cases passed. The
full browser suite then reported 128 passed and four failed: the converted
placeholder photo was 768 pixels wide while the existing natural-size guards
require 1536×1024. The WebP derivative now preserves those original dimensions
(238,600 bytes); the guards retain their original expectations. The three WebP
files now total 1,002,500 bytes. This supersedes the smaller trial derivative's
0.84 MB figure above. Supplied originals remain unchanged.

The four public slash-redirect cases pass locally (16 public-document cases in
total). They require a relative 308 even with spoofed forwarding headers, avoiding
HTTPS → HTTP → HTTPS chains while preserving `proxy_headers=False`. Full local
backend/API verification after the redirect correction passed 588 cases. The
production package and configured static, dependency and secret scans also passed.
Final hosted gates and deployment acceptance remain pending.


### Live home baseline and server-rendered disclosure

Isolated read-only browser audit 39159320624 (2026-10-18 19:34 UTC) used fresh
anonymous Chromium contexts against production v0.15.0. Phone 390: load 1424.1 ms,
response start 335.8 ms, CLS 0.045789. Desktop 1440: load 959.4 ms, response start
134.8 ms, CLS 0.063637. The public feedback-trial flag was true in both contexts.
Artifact 12148466185 contains the public screenshots and metrics; no account was
created, no private account data/cookies were exported, and no purchase occurred.
These samples meet the 2-second load and 0.1 CLS budgets at that test location;
they are not field percentiles or a promise for every network/device.

The candidate now renders the existing public trial availability state into the
initial home HTML via the same `trials.enabled` computation as `/api/session`.
Only the disclosure visibility changes at render time; account/session values are
not embedded and enrollment/consent/billing decisions remain in their existing
handlers. Tests cover enabled/disabled presentation and invalid/duplicate template
markers. The template contract preserves every other hidden panel/form state.

Hosted public acceptance now verifies stylesheet/WebP hashes and captures both
engines at phone/desktop sizes in Light/Dark/Auto, including the home and all new
public pages. It checks exact computed colors, overflow, load <2000 ms and CLS
≤0.1 where the browser exposes that metric, and retains public-only screenshots
and measurements alongside the established hosted release evidence.


Final local runtime rerun after server-rendered availability: `.venv/bin/pytest -q
-m 'not browser'` passed 592 cases (132 browser cases deselected) in 100.85 seconds;
`tests/test_public_pages.py` passed all 20 cases. Formatting, lint/types, 26 frontend
unit tests, production build/package checks and all configured static, dependency
and secret scans passed again. Hosted public browser metrics are written after
each sample so a failing budget retains its measurements. Final hosted source
checks and both deployment acceptance runs remain required before release.


## v0.16.0 source approval and observed staging deployment — October 18, 2026

Final source `bb7891856f5e48b683664c88ae73a9f33c6d2ae7` passed all required application gates in run 39160300781
(job 117772011353): format, lint, Python/TypeScript types, 26 frontend tests,
592 backend/API tests, PostgreSQL integration/exact 36-table backup/restore,
six focused public browser cases, eight appearance, four source-list and 18 mobile
cases, all 132 full browser cases (554.63 seconds), wheel/source/package checks,
Bandit, pip-audit, npm audit and secret scans. Archived legacy run 39160300780
passed 53 tests in its separate environment. No failure or partial run was counted
as a pass; previous placeholder-size failures are resolved with original dimensions.

Artifact 12148841781 was reviewed, including WebKit phone dark checklist, desktop
light FAQ and phone Auto home captures. All six public responsive cases passed.
Retained local Chromium metrics across the checked pages/home had maximum load
61.6 ms and recorded CLS 0; WebKit maximum load was 201 ms, with CLS unsupported.
These are CI lab samples. Appearance, overflow and image/keyboard regressions pass.

Recovery review: production managed Postgres `dpg-dak1lih42hec73blthcg-a` is available
on paid basic_256mb; staging database is also available. Current Render documentation
confirms continuous PITR for paid databases (https://render.com/docs/postgresql-backups).
The connector does not expose a precise recovery timestamp/window. No customer data
was exported or restored; the disposable CI restore passed. This release changes no
schema or database configuration and remains compatible with the preceding runtime.

The existing staging branch was fast-forwarded to the approved source. Render deploy
`dep-dbaicn49v7es738kpiag` is live, finished 2026-10-18 20:05:56 UTC, and reports commit `bb7891856f5e48b683664c88ae73a9f33c6d2ae7`.
Direct HTTPS `/api/version` returned v0.16.0 / staging / that exact commit;
`/api/health` returned status ok, version 0.16.0 and payments_enabled false.
The deployed current-environment row was updated only after these observations.
Hosted account/session/privacy and public browser acceptance are pending at this
ledger event. Production has not yet been promoted.

Direct staged HTTP SEO acceptance also passed (exit 0):
`.venv/bin/python -c "from scripts.check_public_seo import check; check('staging')"`.
All five public documents, internal links, canonical/description/H1 checks, visible
FAQ schema, real 404, protected crawl policy, relative slash redirects and exact
stylesheet/WebP hashes were verified. The first local HTTP root response took
3683 ms; subsequent public documents took 104–108 ms. Those HTTP client samples
are retained separately from browser navigation/CLS budgets; native browser
acceptance is still pending and no universal sub-two-second result is claimed.


## v0.16.0 staged acceptance and observed production promotion

Hosted staged acceptance 39162087913 (job 117777320658) passed exact version,
HTTPS, environment/billing/email mode, four Chromium/WebKit phone/desktop customer
journeys, private/owner boundaries, CSRF rejection, map/list independence, persistent
sessions/cache clearing/browser restart/logout, public HTTP metadata/crawl/404/link
checks and exact public asset hashes. The live research response was partial and
remained labeled as such; this is not proof of complete nationwide availability.
The established checker retains one disposable reserved-domain non-cohort test
account. No real purchase or trial enrollment was performed.

All 48 staged public browser samples passed: maximum load 977 ms and Chromium CLS
0; WebKit does not expose CLS. Phone/desktop Light/Dark/Auto, live device changes,
computed colors and overflow checks passed. Artifact 12148394805 was reviewed,
including WebKit phone dark home and Chromium desktop Auto company page captures.
Cross-environment live smoke 39162087826 also passed while production remained v0.15.0.

PR #41 was squash-merged as `168eb749ae4a2396b98b7b1e48a9862fc915ebb3` only after these gates. Native Git object
lookup proved its entire tree `a83cdce481a03053cde628c98416f0c8c71f3522` equals
approved/staged source `bb7891856f5e48b683664c88ae73a9f33c6d2ae7`.
Production deploy `dep-dbaij9dg1s2s73c896l0` was observed live at 2026-10-18 20:19:46 UTC in the existing
user-confirmed default workspace/service. Both services retain manual deployment.
Existing service/database configuration, environment variables, plans, schema
and billing settings were retained; no existing account entitlement was changed.

Independent read-only production audit 39163023226 observed exact v0.16.0 /
production / `168eb749ae4a2396b98b7b1e48a9862fc915ebb3` and health status ok with payments_enabled true before the
current-environment table was updated. Robots and sitemap returned 200, with the
five canonical public URLs and API exclusion. The anonymous Chromium home audit
(artifact 12149736589) recorded phone 390 load 1367.2 ms, response 296 ms, CLS 0;
desktop 1440 load 970.6 ms, response 141.3 ms, CLS 0.001014. Both contexts confirmed
the public feedback-trial flag true. No account was created by this audit and no
private account/cookie data was exported. These samples are not field percentiles.

The following final hosted production acceptance run verifies the deployed
customer/session/privacy and 48 public browser cases. Its actual result will be
appended after observation; it is not assumed passed at this ledger commit.


## v0.16.0 final hosted production acceptance — Passed

Production hosted release run [39163534677](https://github.com/lupu-spec/Landwolf/actions/runs/39163534677)
(job 117781656708) completed successfully against runtime
`168eb749ae4a2396b98b7b1e48a9862fc915ebb3`, version 0.16.0, on the existing production service.
It checked exact release identity, HTTPS, environment, billing/email mode,
authentication, paywall and owner authorization, Chromium/WebKit phone/desktop
journeys, session persistence, cache clearing, browser restart and logout.
The established checker retained one disposable reserved-domain non-cohort test
account; no real purchase or trial enrollment was performed.

Both hosted commands exited 0:
- `.venv/bin/python scripts/check_hosted_staging.py --environment production --commit 168eb749ae4a2396b98b7b1e48a9862fc915ebb3`
- `.venv/bin/python scripts/check_public_seo.py --environment production`

Public acceptance verified five canonical server-rendered documents, descriptions,
one literal H1, visible FAQ/schema consistency, breadcrumbs/internal links,
image attributes, real 404 responses, production crawl policy, protected API
noindex, relative single-hop slash redirects and exact deployed stylesheet/WebP
hashes. All 48 public browser samples passed across Chromium/WebKit, phone/desktop,
Light/Dark/Auto and live device appearance changes. Maximum warm browser load was
501 ms; maximum supported Chromium CLS was 0.0011111111111111111.
WebKit does not expose the CLS API; its CLS is not represented as a measured zero.

Artifact 12149098801 (`hosted-staging-evidence`, the established artifact name even
for production) was reviewed: desktop Chromium light home, phone WebKit Auto land
research checklist, and the complete public-browser-metrics.json. The home capture
shows the existing enabled feedback-trial disclosure before the sign-in controls;
the public checklist has readable responsive text, visible navigation and attribution.
The independent fresh-context production audit above remains the cold-navigation
sample: phone 1367.2 ms, desktop 970.6 ms. These limited lab samples do not establish
a field percentile or guarantee every visitor loads in under two seconds.

Cross-environment live smoke [39163534662](https://github.com/lupu-spec/Landwolf/actions/runs/39163534662)
passed with both runtimes at v0.16.0. Staging hosted recheck 39163535374 and live
smoke 39163535412 also passed. No code or runtime was changed after the approved
source gates; this evidence update is documentation only and is not a new deployment.
The release table continues to identify staging runtime bb7891856f5e48b683664c88ae73a9f33c6d2ae7
and production runtime 168eb749ae4a2396b98b7b1e48a9862fc915ebb3, not documentation branch heads.

Outstanding external/editorial work: Search Console submission was **not run**:
the secure Google sign-in handoff timed out without an observed authenticated
session or ownership/submission confirmation. The user chose to provide a real bio
but has not supplied biography text; no personal credentials were invented.
Company attribution is present. No backlink outreach was sent and no backlinks
were acquired; the useful public checklist and outreach draft in PUBLIC_SEO.md
are preparation, not earned links. Search ranking by Monday is not guaranteed.

Resolved source failures and unavailable local browser setup are retained above.
The successful native source/browser/security/package gates and both hosted
acceptance runs close the technical release checks; they do not close the external
Search Console, biography or backlink tasks.


## v0.17.0 candidate — seller/broker sources and linked state filters

Implementation adds Zillow/Compass Texas land-page samples and 50 state-specific
Craigslist adapters from the publisher directory (412 regional markets). Static
source metadata drives the main state/category/source controls; original API
authentication, billing, CSRF, owner diagnostics, CRM and schema 13 are preserved.
New publisher records carry availability/classification warnings and enter Hunt
Needs review. No photos, seller contacts or full descriptions are imported.

Passed explicit direct-source trial: `.venv/bin/python
scripts/check_commercial_sources.py --sample-regions` returned exit 0 for all 52
source checks (one regional page/state; 577 supported rows total). It is not a full
regional or nationwide-inventory proof. Full read-only regional checker completed
all 52 checks successfully, returning 3,620 supported rows across the 412 reviewed
Craigslist markets plus Zillow (41) and Compass (5) samples. Full coverage means
all reviewed regions were requested, not complete listing pagination. Some regions
had zero supported matches; missing fields stay unknown. Aggregate-only logs are
in test-results/commercial-live*.json.

Local source parser/API tests initially passed 76 cases; additional Hunt/location
and atomic multi-region regressions were then added for the final gate run.
Early mypy annotations, test line formatting, and a Craigslist canonical-URL/parser
assumption were corrected; these earlier failures are not counted as passed gates.
The production adapter returned 41 Zillow, 68 Dallas Craigslist and 5 Compass rows
in the initial live check before the 50-state expansion. Scope and limits are in
COMMERCIAL_SOURCES.md. Source refreshes retain last-good snapshots and quarantine
anomalous changes.

Current source/package/browser/security gates and the disposable CLI-wide sync
are pending at this candidate documentation event. Staging and production remain
v0.16.0; this candidate is not deployed. Observed final results and deployment
identities will be appended after completion.

Local final gates passed format/lint/types, 27 frontend unit tests and all 670
backend/API tests (108.27 seconds). Wheel/source build and check_package passed;
Bandit, pip-audit and npm audit passed (no known dependency vulnerabilities).
Secretlint rejected a synthetic BasicAuth test URL; the regression now uses a
username-only invalid URL to test credential rejection without embedding a
credential literal. No scanner exclusion or rule change was made. Secret scan
recheck and native gates are required for the updated candidate.

Local focused browser invocation `.venv/bin/pytest -q -m browser
tests/test_commercial_browser.py -x` failed before executing the journey because
the Chromium executable is unavailable. Native CI installs the real browsers;
this local result is an unavailable verification gap, not a pass.

The explicit disposable CLI-wide sync exited 0: all 60 automated feeds were ready,
with 3,902 normalized records and no failed source. The database was
/tmp/landwolf-v17-source-verification.db; no hosted/customer database was accessed.
Final review added fail-closed conversion of malformed nested publisher objects
and excessive JSON nesting into SourceUnavailable so source failures cannot stop
the shared scheduler. Four additional malformed-shape cases were added; the empty
list-coordinate fixture initially exposed a permissive shape conversion, which was
fixed with explicit object validation rather than weakening the assertion. Final
focused tests and security scans are rerun; native final gates remain pending.
Hosted acceptance now also checks static source metadata privacy and all 50
Craigslist choices, plus staged linked state/source filtering and reset.

Native initial browser run 39181126308 failed all four new cases at the final
Reset click: the test assumed Reset was visible with nonempty results, but the
existing UI exposes it only in the empty state. The preceding sign-in, source
filtering, cross-state selection, original link/detail and appearance captures
succeeded. The tests and hosted checker now create a real no-match filter and
assert the empty state before clicking Reset; no forced click, skip, expected
result weakening or production UI change was used. Final native gates must rerun.

Recovery compatibility: the new runtime reads older payloads without a schema
migration, but v0.16 does not recognize seller_listing/new publisher status values.
After ingestion or account-owned research cases exist, do not blindly deploy an
old v0.16 artifact or delete user research to roll back. A recovery build must
retain v0.17 contracts while disabling/reverting the collector behavior as needed.


### Provider terms review and launch scope correction

Review of actual Zillow, Craigslist and Compass terms after the read-only trials
found restrictions on automated collection and commercial redisplay. No provider
agreements were supplied. Trial counts above establish parsing only, not permission.
All commercial collectors now default to disabled; only validated licensed source
IDs can enable one. The manual checker exits 2 without an HTTP client when none
are configured. The eight government collectors remain enabled. No further
publisher collection is run without agreement scope.

Main-screen controls expose publisher search links: 50 Craigslist state choices
with all 412 reviewed markets, plus Zillow and Compass Texas. Numeric filters must
be applied on the publisher site. New browser tests cover disabled-mode links,
keyboard disclosure, state switching and Light/Dark/Auto at phone/desktop sizes.
Prior native runs are not final approval; all gates must rerun for this change.
No v0.17 deployment has occurred yet.

Local scope-change checks: format, lint, mypy, TypeScript and 27 frontend tests
passed. The new checker regression initially failed because pytest does not put
scripts/ on its import path; it now loads the actual script with runpy and the
focused suite passed (87 tests). Full API checks are rerunning after that fix.
A local Chromium installation failed with truncated downloads; WebKit's focused
invocation failed before the journey because host browser libraries are missing.
These are unavailable local browser checks, not passes; native CI supplies both
browsers and remains required. No browser test is skipped or weakened.


### v0.17.0 verified source release — observed staging event

Source commit 61febfe5a02b398db4dbae4922936283aa869378 passed complete native
application run 39182934783: format/lint/types, 27 frontend and 679 backend/API tests;
PostgreSQL integration and exact pg_dump/restore digests across 36 tables; eight
focused source/browser cases and all 140 full browser cases; production build,
wheel/source packaging, Bandit, pip-audit, npm audit and secretlint. Separate
archived regressions passed 53 cases. Phone/desktop publisher screenshots from
artifact 12157303664 were visually reviewed; all three appearance modes and both
engines are covered. The local browser installation/launch gaps above remain
historical failures, resolved for release verification by actual native browsers.

A final v0.17 disposable command exited 0:
`LANDWOLF_DATABASE_URL=sqlite:////tmp/landwolf-v17-release-source-check.db LANDWOLF_LICENSED_LISTING_SOURCES='[]' .venv/bin/python -m landwolf.cli sync`.
All eight original government feeds were ready with 282 records and no publisher
imports enabled. Earlier local HTTP502 and independent native USDA timeout were
retained; recovery was verified before promotion. No hosted database was accessed
by this sync. All local final format/lint/type/frontend/API/build/package/security
commands passed and git diff --check was clean; source tests passed 87 cases.

Render staging deploy dep-dbanchk9v7es7396s5rg became live at
2026-10-19 01:46:54 UTC, runtime commit 61febfe5a02b398db4dbae4922936283aa869378.
The default workspace and existing isolated service/database were retained.
Hosted acceptance is pending; production still runs v0.16.0. The header CSS
candidate is separate and has not been deployed by this source release.

Direct staging HTTPS observation passed: /api/version returned v0.17.0, staging,
and exact runtime 61febfe5a02b398db4dbae4922936283aa869378; /api/health returned
ok, v0.17.0 and payments_enabled false. API ref updates did not produce a hosted
workflow run for the ledger commit. Hosted acceptance gains an explicit
pull_request trigger limited to RELEASES.md on staging/main; the environment is
selected from the PR base (or push branch). Existing push triggers and all checker
assertions remain unchanged. A ledger-only PR runs the established checks against
the observed runtime; no application behavior or deployment changes are included.

Staging hosted acceptance run 39187139290 passed (job 117851834280): four
Chromium/WebKit 390/1440px customer journeys, all 50 Craigslist choices and metadata
privacy, linked state/source selection, native publisher disclosure, no-match/reset,
live mapped inventory, research/CSRF, owner-only boundaries, persistence/cache/
restart/logout. All 48 public browser samples passed; maximum load 638.7 ms,
maximum supported Chromium CLS 0.001112; WebKit CLS is unsupported. These are lab
samples, not field guarantees. One disposable non-cohort verification account was
retained; no owner grant, purchase or existing customer-data export/reset occurred.

PR #42 merged as b5fa49aa57cd7461ea753833dd82cc81517e4ef9. Native Git lookups prove
its complete tree equals source/staging 61febfe5a02b398db4dbae4922936283aa869378
(tree 6b98b5ed0be60a898ca1f9c233555ba014c6a524). Production deploy
 dep-dbangsks728c738rn9f0 became live at 2026-10-19 01:55:51 UTC on that commit.
Existing service, database, live-only payment configuration and manual deploy mode
were retained. Hosted production acceptance is pending; no v0.18 CSS deployment
is claimed. Ledger/document commits do not relabel either runtime commit.

### v0.17.0 production acceptance complete

Native production run 39187665620 (job 117853406374) passed exact v0.17.0 identity,
commit b5fa49aa57cd7461ea753833dd82cc81517e4ef9, HTTPS, production environment,
healthy database, live billing mode and expected email configuration. Four actual
Chromium/WebKit customer journeys at 390/1440px passed authentication, owner-only
coverage/privacy boundaries, unpaid-customer paywall, logout, and persistence after
cache clear/browser restart. Static source metadata covered all 50 Craigslist
choices with no operational/customer data exposure. No charge or owner grant was
created. All 48 production public browser samples passed: maximum load 912 ms,
maximum supported Chromium CLS 0.001014; WebKit CLS unsupported. Public documents,
crawl policy, metadata/schema/links, exact themes and genuine 404 checks passed.

Local production HTTP observation returned status 200 text/html Site Unavailable,
so its JSON decode failed and it is not a local health pass. Independent native
production checks succeeded against the exact expected commit and health response;
that successful external verification establishes runtime health. The local access
limitation is retained rather than silently treated as a successful command.

The v0.17 source release is complete in both environments. Runtime commits remain
staging 61febfe5a02b398db4dbae4922936283aa869378 and production
b5fa49aa57cd7461ea753833dd82cc81517e4ef9; subsequent ledger/CI-trigger documents are
not new application deployments. Both manual deploy settings, existing services,
account/CRM databases, live-only payments, trials and privacy controls are retained.
The v0.18 CSS candidate remains separate and under full regression verification;
no v0.18 staging/production deployment is claimed here.


## v0.18.0 header CSS follow-up — candidate, not deployed

The bounded header/navigation consolidation from PR #40 is reconciled onto the
current source-flow candidate, retaining approved SEO and source changes. It
removes 38 CSS lines and adds seven, reducing .site-header rules from seven to
three without changing theme/breakpoint/keyboard contracts. Versions advance
only for LandWolf itself; third-party dependency metadata is retained.

Inspection of focused run 38994952816 confirms Chromium passed exact independent
render comparisons. WebKit failed at owner width 1001 because the fixture account
hit HTTP 429 after repeated reloads. The comparison now paces paired owner loads
at least 2.2 seconds apart, respecting the real 60/minute search limit. No server
limit, assertion, baseline, screenshot tolerance or test selection is weakened.
The full application CI budget increases to 45 minutes for additional coverage.
All final gates remain required before staging and production.

Local v0.18 checks passed: uv sync --frozen --dev, uv lock --check, npm ci;
Ruff/Prettier format, Ruff/ESLint lint, mypy/TypeScript, 27 frontend and 679 API
cases; production browser build, Python wheel/source build and package validation;
Bandit, pip-audit, npm audit and secretlint; git diff --check. Focused local header
browser launch failed because Chromium is unavailable, before comparisons.
Native full/focused browser, PostgreSQL/restore and archived checks remain pending.
Hosted acceptance now checks hashes of both stylesheets, Auto device changes and
guest/customer phone/desktop header/dock screenshots, retaining the existing
privacy, payment and research journeys.

Default-only disposable CLI sync was run twice with licensed source IDs empty.
Both exited 1: seven original government feeds succeeded (262 records), while
USDA returned HTTP 502 at searchSFH. All 52 publisher sources remained directory
links with imports disabled. The existing failure/last-good behavior was retained.
An isolated native verification branch runs the same unchanged collectors from
GitHub's network to distinguish local access from upstream failure. This live
check is failed, not a pass; no hosted database or customer records were touched.

Native focused run 39183298613 failed the exact phone owner dock image despite
matching all computed header properties. Artifact 12156918738 was inspected:
24,719 pixels differed across the 360x105 translucent dock, with different underlying
page content. Git comparison confirms the obsolete v0.15 styles target h1/JPEG,
whereas approved deployed v0.16 uses h2/WebP. The immutable baseline is corrected
to actual production 168eb749ae4a2396b98b7b1e48a9862fc915ebb3 to preserve those
already shipped SEO changes on both sides. No mask, tolerance or assertion removal
is introduced; all exact regressions rerun. Earlier failures are retained.

Independent native government check 39183615132 also exited 1: USDA ConnectTimeout;
the other seven government feeds were ready. This confirms an upstream/access
limitation beyond the local HTTP502 result. All publisher imports remained disabled.
Required live-source verification is not passed; deployment remains pending.

The source-only candidate 61febfe5a02b398db4dbae4922936283aa869378 passed native
run 39182934783: 27 frontend, 679 API and all 140 full browser tests; PostgreSQL,
exact 36-table restore, packaging/security, plus 53 separate archived tests.
Source screenshots were reviewed at phone/desktop widths. No publisher imports
were enabled. USDA recovered: a fresh disposable v0.18 CLI sync exited 0 with all
eight original government feeds ready and 282 records; earlier failures are retained.

Combined v0.18 run 39183956547 passed focused exact header comparisons (62 pairs)
but failed its full browser gate: 141 passed, one Chromium guest-short screenshot
mismatch. Package/security stages after that browser failure were skipped, not
passed. Retained PNG analysis found 35 rounded-edge pixels different (maximum
channel delta 21/255) despite identical computed styles/rectangles. The test now
awaits font/image decoding and uses official Chromium deterministic compositor
flags without BeginFrameControl. No tolerance, mask, assertion removal or retry
to match is added. All gates rerun; no CSS deployment is authorized by this failed run.


### CSS branch reconciliation after the independent source release

v0.17 is now live and accepted in staging/production. Its observed ledger and
hosted-ledger PR trigger are retained from main 2f49fa753861ee171079a6e64a703ad090ecdc2b.
All earlier v0.18 candidate failures above are historical; v0.18 is still not deployed.
This reconciliation changes only documentation and hosted-check event routing.
The application, tests, build/dependency files and application CI are byte-identical
to tested CSS source 627e0e08585de56380e9b254d839fb132f7fda6d, whose full browser
run remains pending. No CSS release is claimed until its required gates pass.


### v0.18.0 full verification passed; observed staging

Final source 627e0e08585de56380e9b254d839fb132f7fda6d passed complete native run
39186749900 (verify job 117850673701): format/lint/types; 27 frontend and 679 API
cases; PostgreSQL integration/exact 36-table backup/restore; eight commercial,
six public, eight appearance, four source-list and 18 mobile focused cases; all
142 full browser cases; production package validation and every security scanner.
Separate archived tests passed 53 cases. Focused header job 117850673888 also passed.
Artifact 12158412312 contains 62 exact approved/candidate pairs; local byte checks
confirmed all matched, and phone/desktop images were visually reviewed. Full browser
evidence is artifact 12158723592. No masks, tolerances, changed visual assertions
or retries-to-match were introduced; earlier failed runs remain recorded above.

After the capture fix, local commands passed again: Ruff/Prettier format, Ruff/
ESLint lint, mypy/TypeScript, 27 frontend/679 API tests, npm build, Python build/
package validation, Bandit, pip-audit, npm audit and secretlint. git diff --check
was clean. The local browser launch limitation above remains a failed local
invocation; actual native Chromium/WebKit establish the browser verification.

Runtime e12d187b456b90da1936d129f5ff7e62267db0ec reconciles only v0.17 observed
ledger/hosted-event routing. git diff --exit-code against verified source 627e0e0
passed for all landwolf/web/tests/scripts, package/dependency files and application
CI. Render staging dep-dbanseajnfac738eu9h0 became live at 2026-10-19 02:20:46 UTC.
Direct HTTPS /api/version matched v0.18.0, staging and exact e12d187; /api/health
matched ok, v0.18.0 and payments_enabled false. The existing default workspace,
service/database, source/billing/CRM contracts and manual deploy mode were retained.
Hosted staging acceptance is pending. Production remains verified v0.17.0.

Staging hosted run 39189767343 (job 117859787059) passed exact v0.18 identity/health,
hashes of styles.css and graphite.css, Auto device-dark/device-light transitions,
guest/customer phone/desktop header/dock captures and all retained authentication,
source/state, owner-only privacy, CSRF, research, persistence/cache/restart/logout
checks. All 48 public browser samples passed: maximum load 401 ms, supported
Chromium CLS at most 0.001112; WebKit CLS unsupported. Existing source import guards
and customer data/billing behavior were retained; no purchase or owner grant.

PR #40 merged as 7e8aaa71e3fb60948657622273c11dc135aad53c. Native commit lookup
proved its complete Git tree equals staged e12d187b456b90da1936d129f5ff7e62267db0ec
(tree dbb09772a5c2799c62f201d7edb51551e4a28259). Production Render deploy
 dep-dbao0mmq1p3s73cdvjqg became live at 2026-10-19 02:29:35 UTC on that commit.
Production hosted acceptance remains pending. Existing default workspace, manually
deployed services, databases and protected source/account/billing/CRM contracts
were retained. Subsequent ledger documents do not relabel either runtime.

### v0.18.0 acceptance complete in both environments

Independent production run 39190339428 (job 117861529054) passed exact runtime
v0.18.0 / 7e8aaa71e3fb60948657622273c11dc135aad53c, HTTPS, production environment,
healthy database, live payment mode and expected email delivery mode. Both deployed
CSS file hashes matched; Auto followed dark/light device changes; four actual
Chromium/WebKit phone/desktop customer journeys retained header/dock captures,
owner-only privacy restrictions, unpaid-customer paywall, logout and persistent
sign-in after cache clear/browser restart. Static source choices retained all 50
Craigslist options without operational/customer data exposure. No purchase, owner
grant, customer export or data reset was performed.

All 48 production public browser samples passed exact themes, load/layout budgets,
documents/crawl policy/metadata/schema/links and genuine 404 checks. Maximum load
853 ms; maximum supported Chromium CLS 0.001112; WebKit CLS unsupported. These
remain lab samples, not universal field guarantees. The reconciled staged/runtime
source also passed complete application run 39188135828; its metadata reconciliation
introduced no runtime/test/build differences from verified source 627e0e0.

v0.18 runtime identities remain staging e12d187b456b90da1936d129f5ff7e62267db0ec
(Render dep-dbanseajnfac738eu9h0, live 2026-10-19 02:20:46 UTC) and production
7e8aaa71e3fb60948657622273c11dc135aad53c (Render dep-dbao0mmq1p3s73cdvjqg,
live 2026-10-19 02:29:35 UTC). Their complete Git trees match. No application
redeployment follows the documentation-only sign-off commits; manual deploy mode,
existing databases/services and protected account/billing/CRM contracts are retained.
The source-flow release and bounded header consolidation are complete. Prior local
browser/access limitations and resolved native failures remain recorded above.


## v0.24.1 — Audit Desk footer link published

Adds Audit Desk to the homepage footer, opening the existing private app in a
protected new tab. The direct support link retains a 44px touch target when the
navigation wraps. No dependency, schema, account, billing or infrastructure changes.

- Candidate `df350b6bf191c65f9e69593fb025ab38e9987d52`; [PR #55](https://github.com/lupu-spec/Landwolf/pull/55).
- Staging `eeb25dfbea198d5ddf19f3e28395ed8af3a29d14`, Render `dep-dbnv6t6417fc73erhi6g`, live 2026-11-08 03:59:53 UTC.
- Production `9c8d08b229d343ff821e06b3cba322c1fb5e7398`, Render `dep-dbnv8ojrjlhs739vt6c0`, live 2026-11-08 04:03:40 UTC.
- Candidate, staging and production have the same complete tree `f6d31da2b85ad3285c1fbea9caf5519ae8b71a0e`.
- Corrected [application CI 42441901616](https://github.com/lupu-spec/Landwolf/actions/runs/42441901616)
  passed 783 backend/API, 28 frontend, 172 full browser cases, the four early
  mobile accessibility journeys, exact header comparison, PostgreSQL integration,
  49-table backup/restore, builds/packages and clean security checks.
  Factory 42441901649 and legacy 42441901635 passed.
- First application run 42439024989 failed four mobile target-size cases; that
  failure is retained. The support target was corrected and the affected journeys
  moved to the start of browser CI without removing any existing gate.
- Actual Factory PDCA controller reached ACT after one implementation repair.
  This is internal verification, not independent human acceptance.
- Read-only live staging and production checks passed exact version/commit,
  health, billing mode and a unique footer destination with new-tab protections.
  No runtime warning/error appeared in the sampled production app-log window
  04:03:40–04:04:23 UTC. No charge or real customer interaction was performed.

Command outcomes, failed attempts, proof JSON and retention details are in
`app/docs/AUDIT_DESK_FOOTER_RELEASE.md` and `app/docs/AUDIT_DESK_FOOTER_EVIDENCE.json`.
Hosted fixture browser coverage is distinct from a physical-device test; the
live read-only proof checks returned markup, not computed layout. The prior
0.24.0 image remains schema-compatible. This documentation update is not a redeploy.



## v0.24.2 — Retail Watch footer link published

Adds one Retail Watch link beside the completed Audit Desk footer link, preserving
the private apps' ordinary URLs, new-tab protections and existing navigation.
Retail Watch access policy, publication, collectors and experiment records are unchanged.

- [PR #56](https://github.com/lupu-spec/Landwolf/pull/56); candidate `5fc6ae5265aa5d050c635489052a0497c74747be`.
- Staging `d375ee9346320d9890d31aeb27456db67b437984`, Render `dep-dbo06uff3r2c739qpup0`, live 2026-11-08 05:08:13 UTC.
- Production `2562941200eff7ea3944480d89ca09b844218501`, Render `dep-dbo07tqjnfac73difshg`, live 2026-11-08 05:09:59 UTC.
- Candidate, staging and production share complete tree `87a855e101b63ff9fdfe672e4065461f6a90debb`.
- Application CI 42446911747 passed 784 backend/API, 28 frontend and 172 full browser
  cases, early mobile checks, independent header comparisons, PostgreSQL/49-table
  restore, formatting/lint/types, production packaging and security. Factory
  42446911790 passed 36 tests; legacy 42446911677 passed 53.
- Read-only staging and production proofs passed exact version/commit/health,
  environment/billing mode, unique correct footer links, protected new tabs,
  supplied branding asset hashes and production www HTTPS identity.
- Actual pinned L91 PDCA controller reached ACT with zero application repairs.
  Application CI took 37m 09s; full browser suite 26m 07s. Deployments took about
  68 seconds staging and 48 seconds production.
- Local AI was unavailable through the current control connection; no local
  inference ran. Model, hardware, token/throughput and cost metrics remain unknown.
  Cloud-authored code passed independent executable checks. Failed setup attempts
  and the audit helper's formatting correction are retained.
- CI mobile/desktop fixture screenshots were visually reviewed. Live proofs check
  returned markup, not computed layout or physical devices. No warning/error appeared
  in the bounded post-release app-log samples. No schema/account/billing or
  infrastructure change; the prior 0.24.1 image remains schema-compatible.

See [commands, evidence and limits](RETAIL_WATCH_FOOTER_RELEASE.md),
[factory performance](factory-runs/retail-watch-footer-20261108/factory-performance.json)
and [local AI record](factory-runs/retail-watch-footer-20261108/local-ai.json).
This documentation-only sign-off does not redeploy or relabel observed runtimes.



## Unslopovich beta candidate — 2026-11-15

See [UNSLOPOVICH_BETA.md](UNSLOPOVICH_BETA.md) for exact local commands,
partial passes and blocking failures. This candidate is not released.
