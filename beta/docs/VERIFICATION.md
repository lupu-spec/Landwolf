Warning: truncated output (original token count: 35871)
Total output lines: 2075

# LandWolf beta verification

## v0.4.0-beta.4 — visible Hunt saving, 2026-09-28

The creation form explicitly labels its save action and the persistent Hunt list.
Successful creation and editing now confirm the saved destination; browser
regression assertions check the creation, saved, and edit labels at 390px and
1280px, along with the existing API save and retry journey.

**Passed locally:** `npm run format`, Ruff format check, `npm run format:check`,
Ruff lint, `npm run lint`, mypy, `npm run typecheck`, `npm run test:unit`
(7 passed), `.venv/bin/pytest -q -m 'not browser'` (286 passed), `npm run build`,
Python build/package check, Bandit, pip-audit, npm audit, secretlint,
`uv lock --check`, and `git diff --check`.

**Failed locally:** `.venv/bin/pytest -q -m browser -k test_hunt_browser_flow`
could not launch Chromium because the executable is absent. Hosted CI exercised
the browser, PostgreSQL, restore, root test and release preflight before
deployment. Live source sync was not repeated for this wording-only change.

**Passed hosted:** [beta gates](https://github.com/lupu-spec/Landwolf/actions/runs/36500138618)
completed all required steps, including browser, PostgreSQL integration, restore,
package and security. [Root test](https://github.com/lupu-spec/Landwolf/actions/runs/36500138690)
and [release preflight](https://github.com/lupu-spec/Landwolf/actions/runs/36500138656)
passed. PR #7 merged as `834f92ea276c29dd5c98fd5cc2de6b77621e3aea`.
Render deployment `dep-datft6dg1s2s7397ooq0` became live at 23:57:02 UTC.
Direct HTTPS `/api/version` returned `0.4.0-beta.4` and the exact commit;
`/api/health` returned `ok`, and the served HTML contained the save CTA and
saved-list heading. Production was not deployed. A direct production HTTPS
request from this workspace returned a network intermediary's “Site Unavailable”
page; hosted smoke supplies the independent production check.

## v0.4.0-beta.3 — Hunt result cards, 2026-09-28

Individual result cards now display the listing title, acreage, source price
meaning, location and a thumbnail. The app's existing approved-image policy and
default image handle absent, disallowed and failed URLs. Confirmed results omit
fit badges and repeated eligibility prose; records needing review retain their
specific evidence gaps. The backend continues using the same score for in-app
change checks. New API and browser regressions cover image provenance, fallback,
mobile layout and plain titles.

**Passed locally:** `npm run format`; Ruff format/check/lint; Prettier, ESLint,
mypy and TypeScript; `npm run test:unit` (7 passed);
`.venv/bin/pytest -q -m 'not browser'` (286 passed); `npm run build`;
`.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py`;
`.venv/bin/bandit -r landwolf -q`; `.venv/bin/pip-audit --local --skip-editable`;
`npm audit --audit-level=moderate`; `npm run secrets`; `uv lock --check`;
`git diff --check`. The exact Ruff/Prettier/ESLint/mypy/TypeScript invocations
are the required commands in `beta/AGENTS.md` and GitHub beta CI.

**Failed locally:** `.venv/bin/pytest -q -m browser -k
test_hunt_result_photos_and_plain_titles` could not launch because Chromium is
absent. An initial fixture run accidentally used an image URL as the SQLite URL;
the fixture was corrected and reached the browser-launch gate on rerun.
**Not run locally:** PostgreSQL integration/restore, full browser suite, legacy
root environment, and live source sync. Hosted CI supplied the release gates.

**Passed in hosted CI:** [beta run 116](https://github.com/lupu-spec/Landwolf/actions/runs/36483381497)
completed the required browser, PostgreSQL integration, restore, packaging and
security gates. The separate [root test](https://github.com/lupu-spec/Landwolf/actions/runs/36483381503)
and [release preflight](https://github.com/lupu-spec/Landwolf/actions/runs/36483381545)
passed. The 390px and 1280px Hunt screenshots were inspected: titles are plain,
the review card keeps its missing-fact reason, the default image appears where
needed, and the card layout has no horizontal overflow. The browser regression
also asserted an approved image preview, a broken link fallback, an absent link
fallback and a disallowed link fallback.

Render deployed merge commit `19623b48ffc3ff4c97223feb8109cf7885b00cdc` as
`dep-datddlfavr4c73d3pvng`, live at 2026-09-28 21:07:29 UTC. Direct HTTPS
`/api/version` reports `0.4.0-beta.3` and that commit; `/api/health` reports
`ok`. Production was not deployed. Images remain limited to approved source URLs;
Hunt inventory coverage is still partial and alerts remain in-app on demand.

## v0.4.0-beta.2 — Hunt simpler form, 2026-09-28

The Hunt form now defaults to state, acreage band and optional budget, with an
automatic name. Advanced fields preserve county, coordinate radius, custom range,
sale mode and price-per-acre editing. Quick starters, automatic results, cancel
editing and failure retry support the journey. Existing multi-state and preferred
acreage settings survive edits when the corresponding simple criteria are unchanged.
Browser coverage includes mobile/desktop, invalid acreage, conflicting geography,
server failure with retained input, retry, cancel and auction budget wording.

**Passed:** `npm run format`, `.venv/bin/ruff format --check landwolf tests scripts`,
`npm run format:check`, `.venv/bin/ruff check landwolf tests scripts`,
`npm run lint`, `.venv/bin/mypy landwolf`, `npm run typecheck`,
`npm run test:unit` (7 passed), `.venv/bin/pytest -q -m 'not browser'`
(286 passed), `npm run build`, `.venv/bin/python -m build`,
`.venv/bin/python scripts/check_package.py`, `.venv/bin/bandit -r landwolf -q`,
`.venv/bin/pip-audit --local --skip-editable`, `npm audit --audit-level=moderate`,
`npm run secrets`, `uv lock --check`, `git diff --check`.

**Failed locally:** `.venv/bin/pytest -q -m browser -k test_hunt_browser_flow`
could not launch because the Playwright Chromium executable is absent. Earlier
attempts had also hit socket/proxy restrictions; the API, package and audit reruns
above resolved those earlier gaps. **Not run locally:** PostgreSQL integration,
restore, full browser suite, legacy tests and live source sync. Hosted CI is the
release gate for those checks. This documentation also restores historical verification
text accidentally truncated by the previous deployment-ledger commit.

**Passed in hosted CI:** [beta run 112](https://github.com/lupu-spec/Landwolf/actions/runs/36412882516)
completed the full required sequence, including `.venv/bin/python scripts/check_postgres.py`,
`.venv/bin/python scripts/check_restore.py`, `.venv/bin/pytest -q -m browser`,
package validation and all security scanners. The separate root `PYTHONPATH=. pytest -q`
and release preflight jobs passed. The phone (390px) and desktop (1280px) Hunt
screenshots were inspected; no horizontal overflow or hidden main controls appeared.

Render deployed merge commit `d53dadee4f1e0b50d8513ea31e254e82479ea440` as
`dep-dat4ist9fdbs73flugo0`, live at 2026-09-28 11:04:10 UTC. The HTTPS
`/api/version` reports `0.4.0-beta.2` and that commit; recent Render error logs
were empty. Production was not deployed. Public inventory coverage remains partial,
city/ZIP geocoding is not added, and Hunt notifications remain in-app on demand.

**Passed:** [hosted HTTPS smoke](https://github.com/lupu-spec/Landwolf/actions/runs/36413634232)
at 11:06:26 UTC confirmed beta version/commit, health `ok`, updated Hunt markup and
branding asset integrity; it also confirmed production remained on v0.3.3. The
live-smoke workflow now accepts beta version suffixes and runs for staging ledger
updates. Its YAML and embedded Python syntax check passed locally. Direct local
HTTPS reads were intermittent (version succeeded; a health request timed out),
so the successful hosted checks supply the final health evidence.

**Failed, pre-existing/unrelated:** `.github/workflows/release.yml` reports a
configuration failure without running jobs (run 36413633091). Its legacy
`post_deploy_smoke` and `release_healthy` blocks are outside `jobs`; that file was
last changed in `da59d34` and was not used for this Render beta release. The active
beta, legacy test, release-preflight and live-smoke gates all passed. Live source
sync was not repeated for this UI-only release; no new source-availability claim
is made.

## v0.4.0-beta.1 Hunt candidate — 2026-09-28

The isolated beta candidate adds revisioned Hunts and schema v5. Six Hunt tests
cover score arithmetic, unknown versus failed facts, price semantics, geography
validation, account isolation, repeat checks, and migration from v4. A hosted
browser journey is added for create, review, and pause. Render deployed merge commit `57663a20bd148525bd5515ce28c027e90751791a` to the isolated beta as `dep-dasuvf0jo6nc73didk8g`; it became live at 2026-09-28 04:41:23 UTC.

Local **Passed**: `uv sync --frozen --dev`; `uv lock --check`; `npm ci`;
Ruff format/lint; mypy; Prettier, ESLint, TypeScript; four Node unit tests;
`.venv/bin/pytest -q -m 'not browser'` (286 passed; 19 browser tests deselected);
`npm run build`; Python build and package check; Bandit; pip-audit; npm audit;
secretlint; `git diff --check`. The final focused Hunt suite passed six tests.

Local **Not run**: PostgreSQL disposable integration and backup/restore (no local
CI PostgreSQL service), browser tests (Playwright archive download returned a
truncated file; system dependency installer lacked privileges), live source sync,
and legacy root tests (separate environment). Hosted run 105 passed the browser, PostgreSQL integration, disposable backup/restore, package, and security gates. The isolated beta page visibly reports v0.4.0-beta.1, and no recent Render application errors were found.

The implementation limits and deferred email/scheduler/parcel work are recorded
in [HUNT_BETA.md](HUNT_BETA.md). Production remains on v0.3.3.

## v0.3.3 source refresh reliability — 2026-09-27 (deployed)

Live public-source validation ran against a disposable SQLite catalog, never a
production database. All eight automated sources completed: MnDOT 4, Arkansas 0
(no upcoming catalog entries), Texas GLO 31, USDA 19, Treasury 20, IRS 7, Alaska
170 and Michigan 8 records. The refresh preserves the existing snapshot if a
publisher response later fails validation.

The repair accepts GLO's optional unheaded promotion cell, Treasury's valid
two-letter state abbreviations while excluding non-50-state records, and IRS's
current slug identifiers/unannounced notices without accepting unreviewed URL or
filter contracts. It also serializes catalog writes and records a bounded source
failure reason. Tests cover each new parser variation.

Local format, lint, type, targeted regression, frontend unit/build, package,
Bandit, pip-audit, npm audit and secretlint gates passed. The broad Python suite
was started but did not complete locally after its initial progress, so it is not
claimed as passed; hosted CI remains required for the full suite, PostgreSQL,
backup/restore and browser gates.

Render deployed the exact v0.3.3 commit to staging (`dep-daspmbgjo6nc73cro8g0`)
and production (`dep-daspn8p7lnhs73a8mqk0`), with schema-v4 startup completing in
both environments. The services' automatic source refresh runs after startup; no
source-refresh failure was logged during the observed deployment window.

## v0.3.2 image fallback — 2026-09-27 (deployed)

The owner-provided 1536 × 1024 LandWolf “No Photo Available” artwork is bundled
at `/assets/no-photo-available.png`. The shared card/detail photo component uses it
for absent or disallowed image URLs and for allowed URLs whose image request fails.
Actual official source images remain displayed when available. A Chromium browser
regression checks both fallback paths and detail view at 390px and 1440px.

Local `uv sync --frozen --dev` and `npm ci` completed. Ruff formatting/lint, mypy,
Prettier, ESLint, TypeScript, four Node unit tests, 275 non-browser pytest cases,
bundle build, wheel/source package check, Bandit, pip-audit, npm audit, secretlint,
and `git diff --check` passed. Local Chromium installation failed because the
browser archive download was truncated, so the local browser test did not run.
The [hosted beta gate](https://github.com/lupu-spec/Landwolf/actions/runs/36349823669)
passed its full matrix, including Chromium browser journeys, PostgreSQL integration,
backup/restore, and security checks on runtime commit
`9a738e4965277c0bc83a4dbb72cff0425e57a1d7`.

Render reported the exact revision live in beta as `dep-daso5t7pn0mc7399i94g`
and production as `dep-daso7c0473hc739772b0`. Application startup and schema-v4
readiness appeared in both logs. Independent requests from this workspace were
blocked by its network/browser policy. A separate
[hosted HTTPS smoke check](https://github.com/lupu-spec/Landwolf/actions/runs/36350363603)
passed for production, `www`, and beta version endpoints, confirming v0.3.2 and
the runtime commit, and matched the downloaded fallback PNG to the supplied file.

## Permanent Saved feature removal — 2026-09-19 (deployed)

The owner explicitly requested removal and then confirmed: “Delete it permanently
and push to production.” This supersedes the earlier request to retain saved data.
Removed Saved navigation, card/detail/research Save buttons, manual record forms,
saved search filtering, Saved API routes, serializers and ORM models. Source
address/coordinate handoff, manual Research, sessions and deal scenarios remain.
The source-location helper moved to `landwolf/locations.py`.

Schema v3 permanently drops `lw2_saved_records` and `lw2_saved_properties` in one
transaction, without copying or archiving their data. Fresh databases create neither
table. v1/v2 upgrades and repeated runs are supported; unknown schemas stop before
DDL. No CASCADE is used. Accounts, sessions, listings and source status remain.
Old images are incompatible after migration; use a schema-v3 fix-forward release.
Provider-wide backups retain their existing retention; unrelated database backups
are not purged by this feature removal.

Obsolete feature tests were replaced with absent-route/filter/payload assertions,
v1/v2 deletion and repeat-run checks, preservation and atomic rollback checks.
Browser tests now check absent Save controls/requests at desktop/mobile sizes,
direct address/coordinate Research, source-address prefill with review, reset,
reload, search failure/retry and the existing scenario/map/authentication flows.

Local results (commands from beta unless noted):

| Command | Result |
| --- | --- |
| `.venv/bin/ruff format landwolf tests scripts`; `npm run format` | Passed |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed |
| `npm run typecheck`; `.venv/bin/mypy --no-incremental --cache-dir=/dev/null landwolf` | Passed |
| `.venv/bin/mypy landwolf` | Failed, existing local internal cache error, exit 2; hosted canonical gate required |
| `npm run test:unit` | Passed, 4 tests |
| `.venv/bin/pytest -q tests/test_saved_removal.py tests/test_domains.py tests/test_search.py` | Passed, 76 tests |
| `.venv/bin/pytest -q -m 'not browser'` | Passed, 233 tests; 6 browser cases deselected |
| `.venv/bin/python scripts/check_postgres.py` | Failed locally, disposable database unavailable, exit 1; hosted gate required |
| `npm run build`; `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed; retired implementation excluded from wheel |
| `.venv/bin/pytest -q -m browser` | Failed locally, 6 launch failures because Chromium executable is absent, exit 1; hosted gate required |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable`; `npm audit --audit-level=moderate`; `npm run secrets` | Passed, no findings |
| `git diff --check`; `git status --short` (root) | Passed, expected changes only |
| `.venv/bin/pytest -q` (root) | Failed, legacy environment absent, exit 127 |

An initial test collection failure (shared migration-fixture import) and formatting
findings were corrected before the successful local suite. No verification gate
was weakened. Security review found no new dependencies or secrets, no SQL built
from untrusted input, and no changes to auth/CSRF/host/origin protections. Database
deletion is limited to the two explicitly retired tables.

**Hosted gates passed** on runtime commit
`5f65178540e24f10f49530dbd6ad14d6a9809264`:
[push run 35472690390](https://github.com/lupu-spec/Landwolf/actions/runs/35472690390),
job `105976434729`; PR run `35472692824` / job `105976441808` also passed.
All rebuilt-app canonical commands passed, including `.venv/bin/mypy landwolf`,
`.venv/bin/python scripts/check_postgres.py` against disposable PostgreSQL 18,
and `.venv/bin/pytest -q -m browser` (6 journeys). **243 tests passed:** 233 Python,
4 frontend and 6 Chromium. PostgreSQL migration checks confirmed both retired
tables absent, with pre-existing accounts/sessions/listings unchanged. Packaging,
format/lint/types, security, secret scanning and diff checks passed.

CI screenshot artifact `10593300843` was downloaded and hash-verified:
`0cf32fe1f6f9a8556b11ebb6e2d4b07fce49196487dc568ac563dede8ce51604`.
Mobile Explore and Research screenshots were inspected; Saved controls are absent,
source handoff/manual Research remain usable, and the logo/theme are retained.
Screenshots and browser tests use synthetic upstream records.

**Production deployment `dep-dangjc142hec73eebq10` is live** on the existing service,
serving the exact tested commit. Started 22:16:16 UTC; live **22:16:55 UTC**.
At 22:16:40 UTC the predeploy migration logged:
“Beta schema version 3 ready; retired Saved tables removed; accounts, sessions and
source listings preserved”. No replacement service/database, pricing change or DNS
edit occurred. The v3 migration is the only production database change.

Live command `.venv/bin/python -u /workspace/scratch/bae2278276c6/landwolf-removal-production-smoke.py`
passed (exit 0). Before deployment it created one synthetic QA account/session and
two disposable saved records; credentials stayed in process memory. After deployment:

- The existing session remained authenticated; the same credentials still worked
  after logout/login. QA session was revoked; account remains, credentials discarded.
- Database health returned 200 and payments remain disabled.
- All six retired Saved method/path combinations returned 404 for that authenticated
  session; the obsolete saved-only filter returned 422.
- Search, property detail/source coordinates and all-50-state coverage remained
  accessible; responses contain no saved state.
- HTML/JavaScript/CSS exactly match the tested build and return `no-cache` headers.

Deployed SHA-256:

- HTML: `54d2863c008570c0d6143b9c67ded543d6604b6a242478186b84fd2b633fb031`
- JavaScript: `e81ce77b1a211ab220258397371b1f6840a0a563a7fbc5baec19a10b758d68a5`
- CSS: `f44c92095eed9f26ad61ea8d5b995c9dc6c798253b6d027ffa0c2131fa5e46f2`

The platform sign-in page was reloaded and inspected in the cloud browser; its
copy now describes search/research/scenarios. Authenticated UI verification ran
in hosted Chromium; production authenticated checks used HTTPX. Render's warning/error
log query for 22:16:55–22:19:02 UTC returned no entries. A direct production
SQL metadata query could not connect (connector SSL/TLS-required/EOF failure); no
database allowlist/security setting was changed. Production deletion evidence is
the successful transactional v3 predeploy migration, its log and healthy v3 runtime.
`landwolf.ai/api/health` and `www.landwolf.ai/api/health` again timed out from this
environment after deployment; custom-domain reachability remains **unverified**.

Separate legacy CI remains **Failed**: job `105976442217` / run `35472692933`
cannot import `investment_engine`; job `105976442094` / run `35472692901` cannot
import `numpy`. These failure logs were read and are unrelated to the rebuilt app.

## Explore Save and Research → Saved navigation — 2026-09-19 (deployed)

Triage found Save below each card's photo/details, navigation preserving the prior
scroll position and keyboard focus, and stale Explore cards surviving a failed
Saved request. The Research control already had a click handler; a missing handler
was not established as the cause. The platform production bundle matched the prior
release. No authenticated production browser reproduction was available.

The patch moves the labeled Save button above the photo, shares one navigation
handler between Research's button and the Saved tab, focuses the destination
heading and scrolls to the top, clears prior results while loading, and provides
an explicit retry on failure. HTML/assets now revalidate on requests. Account data,
database schema, source adapters, payments and deal calculations are unchanged.

**Regression established before the runtime patch:** test-only commit
`7f7a0b8a00af8c74a36e299d522c8a45e5defc97`, hosted
[run 35471185769](https://github.com/lupu-spec/Landwolf/actions/runs/35471185769),
job `105972320917`: two new desktop/mobile cases failed at the assertion that Save
must be at the top of the card; the five prior browser journeys passed. The new
cases also exercise the exact Research button, heading visibility/focus, selected
Saved tab, saved-record rendering, empty Saved, failed load and successful retry.
The manual-property journey now clicks that same Research button after saving.

Local command results after the runtime patch (exit 0 unless specified):

| Command from beta unless noted | Result |
| --- | --- |
| `.venv/bin/ruff format landwolf tests scripts`; `npm run format` | Passed |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed (initial long test line corrected) |
| `.venv/bin/mypy landwolf` | Failed, existing local mypy internal error, exit 2 |
| `.venv/bin/mypy --no-incremental --cache-dir=/dev/null landwolf`; `npm run typecheck` | Passed |
| `npm run test:unit`; `.venv/bin/pytest -q -m 'not browser'` | Passed, 4 Node and 235 Python tests |
| `.venv/bin/python scripts/check_postgres.py` | Failed locally, disposable database unavailable, exit 1; hosted gate required |
| `npm run build` | Passed |
| `.venv/bin/pytest -q -m browser` | Failed locally, Chromium executable absent; 7 launch failures, exit 1; hosted gate required |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable`; `npm audit --audit-level=moderate`; `npm run secrets` | Passed, no findings |
| `git diff --check`; `git status --short` (root) | Passed, expected changes only |
| `.venv/bin/pytest -q` (root) | Failed, legacy environment missing, exit 127 |

Diff security review: labels remain text nodes, authentication/ownership/CSRF
checks are unchanged, and API responses retain `Cache-Control: no-store`.
No dependencies, credentials, private records or infrastructure access rules changed.

**Hosted final gates passed on runtime commit
`7943395e09e15a9fdf41de4192681ff3bddc77c7`:**
[push run 35471440084](https://github.com/lupu-spec/Landwolf/actions/runs/35471440084),
job `105973005074`; PR run `35471441912` / job `105973009978` also passed.
All canonical commands listed above passed in the hosted environment, including
`.venv/bin/mypy landwolf`, `.venv/bin/python scripts/check_postgres.py` against
disposable PostgreSQL 18 and `.venv/bin/pytest -q -m browser` (7 journeys).
**246 tests passed**: 235 Python, 4 frontend and 7 Chromium journeys. The package,
format/lint/types, dependency audits, Bandit, secret scan and diff gates passed.
No gates were weakened. Artifact `10593085071` was downloaded and its SHA-256
`215789eb844406cbcc49988fd36be5054fbb5887c72dc8134c4b29dc96b9047d`
verified. Reviewed desktop/mobile Explore and mobile Research→Saved screenshots:
Save is above each photo, Saved has a selected tab and visible heading, and the
original logo/theme remain. These screenshots use explicitly synthetic test data.

**Production:** Render deployment `dep-dang76ek1f9s738kn5ng` serves that exact
runtime commit; started 21:50:17 UTC, live **21:50:59 UTC**. The predeploy log at
21:50:45 UTC confirms schema v2 ready with existing records preserved. No database
migration or replacement was needed for this UI patch.

Command `.venv/bin/python /workspace/scratch/bae2278276c6/landwolf-nav-production-smoke.py`
passed (exit 0) against `https://landwolf-free-beta.onrender.com`. It verified:

- Database health 200, payments disabled, API `Cache-Control: no-store`.
- HTML, JavaScript and CSS exactly match the local production build and carry
  `Cache-Control: no-cache` to revalidate stable filenames after deployment.
- Anonymous Saved access returns 401; a fresh synthetic QA account can save a
  real source listing and a manually entered public address; both appear in Saved.
- Both records and the address survive logout/login. Cleanup removed both QA
  saves and revoked the session. The QA account remains; credentials were discarded.

Deployed SHA-256:

- HTML: `6ca6b95dabeffccaa6ef159792f558fdeab0f18615631ded459da6d128d704b6`
- JavaScript: `0a22cdb562315f7a96b3a938c93d2bb6dd3a47cd20b6ec4a1b8b44cec9783e8e`
- CSS: `3d9b71236b9c38c96407f88b3c40659211c32d4d610fe9a7fb2990ecd9074795`

The production cloud-browser sign-in page loaded after deployment. Authenticated
button clicks were verified in hosted Chromium, not in the production cloud browser.
Render's warning/error log query for 21:50:59–21:53:00 UTC returned no entries,
covering the first two minutes after the deployment became live.
**Custom domains remain unverified:** root/assets requests timed out or returned
502 before deployment; both `landwolf.ai/api/health` and `www.landwolf.ai/api/health`
timed out after deployment. This does not establish an outage for other clients.
Render Dashboard domain inspection required a new sign-in and was not completed;
no DNS records were changed.

Unrelated legacy CI remains **Failed**: run `35471441923` / job `105973009998`
cannot import `investment_engine`; run `35471441922` / job `105973010099` cannot
import `numpy`. Actual failure logs were inspected. The rebuilt application's
passed gates do not mean all repository workflows pass.

## Saved property persistence revision — 2026-09-19 (deployed and live API verified)

Implemented prominent Save actions, manually entered private saved properties,
account-persistent research addresses/coordinates, cross-feed address handoff,
revision conflict checks, and an additive v1 → v2 database migration. The old
frontend address test moved to five server-side source-location cases alongside
new persistence/security tests; the obsolete frontend helper was removed.
No source adapters or deal equations were changed.

**Production outcome:** Runtime commit `08066fa3c41a0ba9ab535e0bc023f1549d952058`
is live on the existing Render service. Deployment `dep-danfms3bc2fs73e8iq7g`
started at 21:15:28 UTC and became live at **21:16:21 UTC**. The predeploy log at
21:16:07 UTC records “Beta schema version 2 ready; existing records preserved”.
No service/database replacement, account reset, billing change or DNS change occurred.

**Hosted gates passed after the test-locator correction:**
[push run 35469711430](https://github.com/lupu-spec/Landwolf/actions/runs/35469711430),
job `105968325037`; the corresponding PR run `35469713083` also passed. Exact commands
are in the local table below and `.github/workflows/beta.yml`. Hosted results:

- `.venv/bin/ruff format --check landwolf tests scripts`, `npm run format:check`,
  `.venv/bin/ruff check landwolf tests scripts`, `npm run lint`,
  `.venv/bin/mypy landwolf`, `npm run typecheck`: **Passed**.
- `npm run test:unit`: **Passed**, 4 tests; `.venv/bin/pytest -q -m 'not browser'`:
  **Passed**, 235 tests; `.venv/bin/python scripts/check_postgres.py`: **Passed**
  on disposable PostgreSQL 18, including the v1 migration, repeat migration, old
  bookmark retention, manual-save retries and location updates.
- `npm run build` and `.venv/bin/pytest -q -m browser`: **Passed**, all 5 journeys.
  The new mobile journey checks a visible Save button, source-address prefill,
  no automatic address research, edited location persistence after reload,
  manual save failure/retry, manual address/coordinate round trips, and removal.
- `.venv/bin/python -m build`, `.venv/bin/python scripts/check_package.py`,
  `.venv/bin/bandit -r landwolf`, `.venv/bin/pip-audit --local --skip-editable`,
  `npm audit --audit-level=moderate`, `npm run secrets`, `git diff --check`, and
  `git status --short`: **Passed**. No known vulnerabilities or secret findings.

**244 tests passed**, plus the PostgreSQL integration script. CI artifact
`10592516871` was downloaded and its SHA-256 verified before inspecting the mobile
Saved, Research and sticky detail-action screenshots. Logo/theme retained; buttons
and saved locations visible; browser assertions found no horizontal overflow.

**Live API smoke passed**, command `.venv/bin/python - <<'PY'` with an HTTPX client
against `https://landwolf-free-beta.onrender.com` (exit 0). It checked health 200,
payments disabled, new HTML controls, unauthenticated Saved 401, fresh QA registration,
saving a real source listing, updating its private research coordinates without
changing the source coordinates, creating/retrying a manual address save, and both
saved records surviving sign-out/sign-in. Cleanup removed both QA saved records and
revoked the session; the synthetic QA account remains. No existing account was used.
Deployed browser assets exactly matched the locally built assets:

- `app.js`: `1d49f8a0653adbf13591664c9fef7b81c56aa7d15fbcb94631e27b779b81ac0a`
- `styles.css`: `ab4118c01d5ba1adccd43329afc810d969cdf5208acf0f4d0e4e8ddbba9a06e7`

**Remaining limitations:** Live browser inspection confirmed the platform-hosted
sign-in page, but no authenticated cloud-browser production journey ran; that UI
flow passed in hosted Chromium with synthetic data. Custom-domain HTTP health
checks timed out for `landwolf.ai` and `www.landwolf.ai`; the cloud browser showed
a connection-refused 502 for the apex. This does not establish an outage for users.
Google DNS-over-HTTPS returned apex A `216.24.57.1`, while `www` still resolves via
CNAME `landwolf-mw8m.onrender.com` (the old host). The desired `www` CNAME is
`landwolf-free-beta.onrender.com`; no registrar record was changed in this patch.
The postdeploy Render warning/error log query failed because Render's Loki log
service returned 502/503, so an error-free production log scan is **not verified**.
Direct production SQL inspection was also unavailable as described below.

Separate legacy workflows remain **Failed**, unrelated to the isolated rebuild:
run `35469713082` / job `105968329735` cannot import `investment_engine`, and
`35469713084` / job `105968329764` cannot import `numpy`; their actual logs were read.
Do not describe the entire repository's CI as passing.

Observed local commands after implementation:

| Command (from beta unless noted) | Result |
| --- | --- |
| `.venv/bin/ruff format landwolf tests scripts`; `npm run format` | Passed, formatting applied |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed after correcting unused/unsorted imports |
| `npm run typecheck` | Passed |
| `.venv/bin/mypy landwolf` | Failed: generated cache SQLite database malformed |
| `.venv/bin/mypy --no-incremental --cache-dir=/dev/null landwolf` | Passed, 16 source files |
| `npm run test:unit` | Passed, 4 tests |
| `.venv/bin/pytest -q tests/test_saved.py tests/test_search.py` | Passed, 31 tests |
| `.venv/bin/pytest -q -m 'not browser'` | Passed, 235 tests; 5 browser tests deselected |
| `.venv/bin/python scripts/check_postgres.py` | Failed locally: disposable `landwolf_ci` URL unavailable; hosted gate required |
| `npm run build` | Passed |
| `.venv/bin/pytest -q -m browser` | Failed: Chromium executable absent; all 5 failed before browser launch |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed |
| `.venv/bin/bandit -r landwolf` | Passed, no findings |
| `.venv/bin/pip-audit --local --skip-editable`; `npm audit --audit-level=moderate` | Passed, no known vulnerabilities |
| `npm run secrets` | Passed |
| `git diff --check`; `git status --short` (root) | Passed; expected patch files only |
| `.venv/bin/pytest -q` (root legacy environment) | Failed: root test environment absent, exit 127 |

Render read-only preflight confirms the existing service uses the rebuild branch,
manual deploys, and `python -m landwolf.cli init-db` before deploy. The connector's
read-only production PostgreSQL query failed with an SSL/TLS connection error;
no production values or records were read or changed. No database allowlist was
relaxed. Hosted PostgreSQL/Chromium and production verification were pending at
this initial checkpoint; final results are recorded above.

First hosted run on `0509feac` ([35469543136](https://github.com/lupu-spec/Landwolf/actions/runs/35469543136))
passed format, lint, types, 235 Python tests, 4 frontend tests and the PostgreSQL 18
migration/persistence check. Four existing Chromium journeys passed. The new
journey stopped at its first save assertion because its locator kept looking for
the old accessible name after a successful save changed it to “Remove saved
property”. The assertion now targets the saved-state name and still requires
`aria-pressed=true`; no test or assertion was removed. The fresh hosted run above
then passed the complete new journey.

## Production release — property workflows (2026-09-19)

Runtime commit `866ff7dbdb07a219980f5cff3b5f598a73f54ad8` was pushed to
`codex/landwolf-beta-rebuild`, verified in hosted CI, then manually deployed to
the existing `landwolf-free-beta` service (`srv-dak1lvh42hec73blur00`).
Render deployment `dep-daneslbm8hqs73b3gha0` became **live at 20:20:21 UTC**.
The code push did not auto-deploy: Render's `autoDeploy=no`, trigger `off`, and
PR previews were confirmed off before pushing. No new Render service/database,
database reset, migration, billing change, or DNS change was made.

### Hosted gates — passed for the deployed commit

The missing Chromium and disposable PostgreSQL infrastructure was provided by
GitHub Actions, not by bypassing this workspace's package-install restrictions.
Local package installation remains restricted; local browser checks remain unavailable.
The isolated runner started PostgreSQL 18 and installed Chromium with its OS dependencies.

[Push run 35466903356](https://github.com/lupu-spec/Landwolf/actions/runs/35466903356),
job `105960801784`, completed successfully. The rebuilt-app PR run
`35466905035`, job `105960806899`, also succeeded.
These exact commands ran successfully in the push job:

| Commands (from beta/) | Observed result |
| --- | --- |
| `pip install uv==0.12.11`; `uv sync --frozen --dev`; `npm ci`; `.venv/bin/playwright install --with-deps chromium` | Passed: isolated locked environments and browser installation. |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed. |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed. |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | Passed. |
| `npm run test:unit` | Passed: 5 frontend arithmetic/location/filter tests. |
| `.venv/bin/pytest -q -m 'not browser'` | Passed: 212 tests; 4 browser tests reserved for the next gate. |
| `.venv/bin/python scripts/check_postgres.py` | Passed against disposable `landwolf_ci`: authentication, nationwide JSON filters, nulls, dates, pagination and saves. |
| `npm run build`; `.venv/bin/pytest -q -m browser` | Passed: 4 Chromium journeys, including save failure/retry, synchronized saved state, zero defaults/acknowledgment, bid overrides, research handoffs, independent filters and mobile layout. |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed: wheel/source archive and required runtime/source/test assets. |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable`; `npm audit --audit-level=moderate`; `npm run secrets` | Passed: no reported vulnerabilities or scanner findings. |
| `git diff --check`; `git status --short` | Passed. |

### Post-deploy observations

An HTTPX check from this workspace observed the following at the Render platform
origin `https://landwolf-free-beta.onrender.com` after the deployment became live:

- `/api/health`: HTTP 200, `status=ok`, `payments_enabled=false`.
- `/`: HTTP 200; new downside/upside, zero-cost acknowledgment and research-context
  fields present.
- `/assets/app.js` and `/assets/styles.css`: HTTP 200. SHA-256 values matched the
  locally built assets exactly:
  - JS: `a651dae7e2886f070319e4550c490a1edd01078bd40aae9b80bdbad7064c1523`
  - CSS: `e36d77181a62c2a63d4e796e19b360de36f92b68db9a7c8c5965502e482f0621`
- Anonymous `/api/properties/verification-no-session`: HTTP 401 as required.
- Render log query returned no warning/error entries between deployment start
  (20:19:33 UTC) and 20:20:59 UTC.

**Verification limits:** `https://landwolf.ai/api/health` and the `www` equivalent
timed out from this workspace. The cloud browser also timed out opening the custom
domain. This does not establish a domain outage, but custom-domain HTTPS/redirects
and authenticated live-browser save persistence were not verified in this release.
No production test account or records were created. CI browser/database tests use
isolated accounts and synthetic fixtures; they do not establish live source coverage.

Separate legacy workflows remain failing and were not changed or claimed as passed:
the legacy Test job failed importing `investment_engine`, and Release Preflight
failed importing `numpy`. The existing legacy release workflow also reported failure.
They are separate from the rebuilt application's successful release gates.

## Local patch preparation — property saving and scenario handoffs (2026-09-19)

Prepared locally against `050ba89a5410c1e6f6d59fa3a2eae845aa3bea2b`.
**Historical local result:** initially not pushed/deployed, with browser and PostgreSQL
checks blocked. The production-release section above supersedes that status.
The historical deployment observations below are not a verification of this patch.

### Behavior and limits

- Card and detail Save/Saved controls share state, prevent duplicate in-flight
  writes, retain server-side account ownership, and show failures without falsely
  confirming a save. Saved and Explore filters are independent.
- Resale defaults to 95% / 100% / 120% of the published price or entered bid.
  Editable percentages and explicit dollar overrides are preserved. These are
  hypothetical bounds, never market valuations or calibrated confidence intervals.
- Per the owner's follow-up, unestimated cost inputs and holding period default
  to zero. The UI requires acknowledgment of zero-cost assumptions, and API
  results independently warn that zero costs can overstate returns and maximum bid.
  ROI/profit/loss targets remain editable preferences. No regional cost dataset or
  statistical cost estimator is connected; no invented figures are presented as evidence.
- Research actions on Search, Saved and property details carry listing context.
  Published coordinates prefill and run; usable IRS/USDA source addresses prefill
  for review. Unknown locations remain blank. Edited research locations are flagged
  as potentially different properties and do not overwrite scenario inputs.
- Similar-property actions prefill state, county, category and minimum acre…15871 tokens truncated…cks;
`.venv/bin/pytest -q -m 'not browser'` (210 passed); `npm run build`; Python package
build and package inspection; Bandit; pip and npm dependency audits; secret scanning;
and `git diff --check`. The first browser-suite attempt ran but failed all three cases
before page load because the Chromium executable was absent. A subsequent
`.venv/bin/playwright install chromium` attempt was interrupted after the approved
download endpoint returned HTTP 502 and then timed out. These are **Failed**, not
passed browser gates. Hosted CI must run and pass the three Chromium journeys before
deployment. No dependency or lockfile changed.

The first hosted browser run checked 900px, outside the affected `max-width: 800px`
rule, and failed the new assertion. The second checked 790px but confirmed that a
hidden `br` still contributed an accessibility-text line boundary. Both runs had two
other browser journeys pass, and neither was treated as verification. The final
implementation replaces those breaks with block/inline responsive spans; a new hosted
run is required before deployment.

The third hosted run showed that Playwright `inner_text()` preserves a line boundary
around the inline span even though the responsive CSS applies. It therefore failed
the sentence-substring assertion while the other two journeys passed. The regression
now asserts the actual rendering invariant (`display: inline`) and uses DOM text with
whitespace-aware matching to prove the words cannot concatenate. A fourth hosted run
is required; the preceding failed runs remain recorded as failures.

Final hosted push run
[35462636178](https://github.com/lupu-spec/Landwolf/actions/runs/35462636178),
job `105949119339`, **Passed** every configured step: locked installs, format,
lint, types, 210 unit/API tests, disposable PostgreSQL integration, all three
Chromium journeys (including the 790px heading-spacing regression), production
package, security scans and diff integrity. Runtime commit
`81b1efb776077ad6063a08501006785f4c1af9b2` was manually deployed because
auto-deploy remains off. Render deploy `dep-dandlm6gekts738ko650` reached **live**
at 18:57:21 UTC on September 19, 2026.

After deployment, the explicit HTTPS check against the Render address exited 0:
`/api/health` and `/` returned 200, payments remained disabled, and deployed HTML/CSS
contained both responsive heading spans and the block-to-inline `max-width: 800px`
rules. Neither joined-word string appeared in the HTML. A bounded Render application
warning/error query covering deployment through 18:57:55 UTC returned zero entries.


## Premium trust beta — September 19, 2026

Scope: isolated `codex/landwolf-premium-staging` branch and
[PR 2](https://github.com/lupu-spec/Landwolf/pull/2). Production resources and DNS
were not changed. Priorities 2–4 are typed extension contracts, not enabled products.

Initial local gates on the priority-one implementation:

| Command (from beta unless noted) | Observed result |
| --- | --- |
| `.venv/bin/ruff format --check landwolf tests scripts` | Exit 0 |
| `npm run format:check` | Exit 0 |
| `.venv/bin/ruff check landwolf tests scripts` | Exit 0 |
| `npm run lint` | Exit 0 |
| `.venv/bin/mypy landwolf` | Exit 2: local cache/internal error |
| `MYPY_CACHE_DIR=/dev/null .venv/bin/mypy landwolf` | Exit 0, 20 source files |
| `npm run typecheck` | Exit 0 |
| `npm run test:unit` | Exit 0, 4 passed |
| `.venv/bin/pytest -q -m 'not browser'` | Exit 0, 264 passed; two dependency deprecation warnings |
| `npm run build` | Exit 0 |
| `.venv/bin/python -m build` | Exit 0 |
| `.venv/bin/python scripts/check_package.py` | Exit 0 |
| `.venv/bin/bandit -r landwolf` | Exit 0, no issues identified |
| `.venv/bin/pip-audit --local --skip-editable` | Exit 0, no known vulnerabilities |
| `npm audit --audit-level=moderate` | Exit 0, zero vulnerabilities |
| `npm run secrets` | Exit 0, including staging Blueprint |
| `git diff --check` (repository root) | Exit 0 |

Local `.venv/bin/playwright install --with-deps chromium webkit` failed (exit 1):
system-package installation denied setgroups/setuid operations. The bounded browser-only
install also failed (exit 1) with CDN timeouts/502. The actual browser command
`.venv/bin/pytest -q -m browser` exited 1: all 16 journeys failed before page load
because their executables were missing. These runs are not browser verification.
Hosted CI installs both engines and must supply the browser evidence.

A disposable SQLite live database was initialized explicitly with `init-db` (exit 0)
after an initial sync failed because the empty database had no tables (exit 1).
The subsequent real `.venv/bin/python -m landwolf.cli sync` also exited 1: seven feeds
were ready, one unavailable. Observed record counts: Arkansas 277, Texas 30, USDA 18,
Treasury 15, Alaska 170, Michigan 8, Minnesota DOT 4; total 522. The IRS adapter failed
closed because the site did not apply the requested real-estate/tax-seizure filters.
A separate bounded diagnostic reproduced that exact parser rejection. No IRS records
were fabricated or imported with unconfirmed filters.

The Minnesota records were 139624 (5.03 acres, September 30 bid opening), 139574
(17,005 square feet converted to acres), 139595 (6.74 acres), and 139662 (17,962 square
feet converted to acres). Asking prices, parcel IDs and coordinates remained null.
Original source links and page-level update dates were retained. Successful retrieval
does not establish continued availability, title, a valuation or complete coverage.

Legacy checks ran in the separate existing legacy environment. Bare `pytest -q`
was unavailable (127); that environment's `pytest -q` without `PYTHONPATH` failed
collection (4). With `PYTHONPATH=.`, the actual run completed: 48 passed, 5 failed,
exit 1. Those five legacy billing tests require absent `.env.live.example` or
`.env.sandbox.example` files. Legacy application/billing tests were not changed.

The Render Blueprint passed JSON Schema validation against
`https://render.com/schema/render.yaml.json` (exit 0) using an isolated tooling
environment. Initial attempts lacked tooling dependencies and then used a nonexistent
SchemaStore URL; neither was a successful validation. Render CLI/platform validation,
container build, hosted staging HTTPS and actual sender delivery are not established
by JSON Schema validation. The Blueprint has not been provisioned.

The first Git push was rejected by automatic approval review until destination
ownership could be established. GitHub confirmed authenticated user `lupu-spec` owns
the public repository and has push permission. The retry passed review but the shell
had no GitHub credential. The authenticated GitHub connector then published the
branch; the remote tree was checked equal to the local committed tree.


First hosted beta run [35475761587](https://github.com/lupu-spec/Landwolf/actions/runs/35475761587)
(commit `fb5b1d6880080f49202d457b805979ff419c3950`) passed locked installs, both
formatters/linters/type checkers, unit/API tests, PostgreSQL integration and exact
row-digest backup restoration across all 11 tables. Browser result: 12 passed,
4 failed. Two failures were 320px coverage overflow with 200% text in Chromium
and WebKit; the other two were test email links navigating within the same document,
so the startup token handler was not invoked. Corrections allow source cards,
filter controls and navigation to wrap, and open email links from a fresh document.
The tests retain their original functional and overflow assertions. Screenshots of
the 390px Explore and 1440px Research views were downloaded and visually inspected;
the source fixtures are synthetic, not live listings. A new passing hosted run is
required for the corrected implementation. The subsequent local backend run passed
265 tests (exit 0), including rejection of unsupported valuations and implicit consent.


Second hosted beta run [35476124085](https://github.com/lupu-spec/Landwolf/actions/runs/35476124085)
(commit `a3bad133d595ecab14dd8bf10f4d74e9b408b628`) passed the earlier code/database
steps again, with 265 backend tests. Browser result: 14 passed, 2 failed. Both
email verification/recovery journeys now passed. Only the 320px doubled-text page
width assertion failed in both engines. Downloaded screenshots measured 329px wide
and showed the oversized Coverage heading extending past its card. The correction
uses a smaller responsive heading, normal text wrapping, and a navigation grid that
stacks based on available space and font size. The horizontally scrollable data
table receives a keyboard focus target and accessible label. Global page-width
assertions remain unchanged; another hosted run is required.


### Final implemented runtime: passed beta gates

[Hosted run 35476407770](https://github.com/lupu-spec/Landwolf/actions/runs/35476407770),
job `105986296342`, completed successfully for runtime commit
`7c1e5947d8cef02a0b2861d61fe9849ba5ac0f00`.

Every configured beta step passed, with exit 0 for its commands: locked environment
installation (`uv sync --frozen --dev`, `npm ci`, Playwright Chromium/WebKit install),
Ruff/Prettier format checks, Ruff/ESLint, canonical `.venv/bin/mypy landwolf` and
TypeScript, `npm run test:unit` (4 passed), `.venv/bin/pytest -q -m 'not browser'`
(265 passed), `.venv/bin/python scripts/check_postgres.py`, and
`.venv/bin/python scripts/check_restore.py` (11 tables restored with exact row digests).
`npm run build`, `.venv/bin/pytest -q -m browser` (16 passed),
`.venv/bin/python -m build`, `.venv/bin/python scripts/check_package.py`,
`.venv/bin/bandit -r landwolf`, `.venv/bin/pip-audit --local --skip-editable`,
`npm audit --audit-level=moderate`, `npm run secrets`, `git diff --check` and
`git status --short` also passed. Security scanners reported no issues/known
vulnerabilities; this is not a guarantee that no vulnerability exists.

Browser coverage: Chromium and WebKit at 320, 390, 768 and 1440 CSS-pixel widths;
authentication, Explore/list defaults, property evidence, Research handoff/summary,
source details and roadmap, county gaps, no horizontal page overflow, and the
coverage page with 200% root text size. Two additional journeys consume real
one-use account tokens with a locally captured test mail transport. Existing
Saved-removal, scenario, map/list and stale-response regressions also passed.
These are emulated viewport checks on Linux engines, not physical-device Safari
certification, a full accessibility audit, or real email-delivery verification.

The run's `beta-browser-evidence` artifact retains screenshots for seven days.
The earlier failed runs remain documented above. Separate legacy workflow/test
failures do not become passes because the beta workflow is green.

Not run/not provisioned: staging service and database creation, a new container
build, Render platform Blueprint validation, hosted staging HTTPS/browser checks,
a staging/production backup restore, real Resend delivery and sender-domain setup.
The public Blueprint JSON Schema check passed separately. As selected by the owner,
resource provisioning follows review of `render.staging.yaml`; no production
service, domain binding or database was changed. The free review database expires
after 30 days; hosted backups require separate configuration. IRS live-filter
validation remains unavailable, and nationwide county/MLS coverage remains partial.


Final screenshot inspection covered 390px WebKit Explore, 1440px Chromium Research,
and the top of the 320px Chromium coverage page at doubled text. Navigation now
stacks without splitting labels across narrow columns, and the Coverage heading
fits its card. Final doubled-text screenshots from both engines measured exactly
320px wide. Large data tables scroll inside their labeled region; no global page
clipping rule hides overflow. Local final diff checks and a repeated secret scan
passed. The follow-up commit changes documentation only; the runtime remains the
one verified by the successful hosted run above.

### Staging provisioning attempt — 2026-09-20

The owner approved the proposed free staging resources. Read-only Render calls
confirmed no staging service exists and an active free `landwolf-db` already
occupies this workspace's free PostgreSQL allowance. The official
[free-resource documentation](https://render.com/docs/free) allows one active free
database per workspace. No create, delete, upgrade or deploy operation was issued.
Production remains unchanged. The Render Dashboard showed its sign-in form;
authenticated connector access does not establish a signed-in browser session.

Prepared `render.staging.paid.yaml` as an alternative requiring approval of an
additional recurring charge. The observed pricing page lists $6/month for
`0.1c-256mb` and $0.30/GB for database storage. The proposal fixes storage at 1 GB,
disables storage autoscaling, blocks external database access, and retains a free
web service, disabled payments/email and disabled automatic deploys.

Verification actually run after this configuration-only change:

- **Passed:** `uv run --no-project --isolated --with jsonschema --with pyyaml python`
  with a stdin script loading both staging YAML files and validating each via
  `jsonschema.Draft202012Validator` against the cached official Render schema at
  `/workspace/scratch/bae2278276c6/render-schema.json`; exit 0.
- **Passed:** `./node_modules/.bin/prettier --check ../render.staging.paid.yaml`,
  `./node_modules/.bin/secretlint ../render.staging.paid.yaml --no-terminalLink`,
  and `npm run secrets` from `beta/`; each exited 0.
- **Failed preliminary tooling probe:** `python -c 'import jsonschema, yaml;
  print("Schema validation libraries available")'`; exit 1 because the default
  Python lacks jsonschema. The isolated command above supplied the tooling.
- **Not run:** Render platform Blueprint validation, new Docker build, provisioning,
  hosted staging health/browser/email checks, or a staging backup restoration.
  Runtime tests were not rerun for this configuration/documentation-only change.
  GitHub beta runs 35476673101 and 35476671217 succeeded on the preceding commit
  `1ce03346c8e457aab24138b97ea82092e4a79338`; these do not validate deployment of
  the new paid alternative. Separate legacy workflows still fail.

### Staging deployed and checked — 2026-09-20

The owner subsequently approved the $6.30/month isolated database. GitHub sign-in
to Render succeeded; the dashboard accepted `render.staging.paid.yaml` and showed
the same estimate before deployment. Created:

- Blueprint `exs-dantsjegekts73a5njc0`.
- Free Oregon web service `srv-dantt23tqb8s73d55dfg`.
- Separate Oregon PostgreSQL 18 database `dpg-dantsp3tqb8s73d54hgg-a`,
  `0.1c-256mb`, 1 GB, storage autoscaling off, external IP allow list empty.
- URL: https://landwolf-premium-staging.onrender.com/ .

Initial deployment `dep-dantt2btqb8s73d55e30` failed with status 127 because Render
treated the nested quoted shell command as an executable name. No schema migration
ran in that attempt. Replaced it with `/bin/sh /app/landwolf/start_staging.sh` in
both staging Blueprints. The script refuses non-staging environments, exits on a
failed migration, and replaces itself with the normal server after success.
Production's entry point is unchanged. Regression tests cover all three outcomes.

Startup runtime commit `10aa75971911f2163f918ea313a8e3421ede07c1` passed all beta
gates in [run 35513575841](https://github.com/lupu-spec/Landwolf/actions/runs/35513575841),
job `106085613310`: 268 backend tests, 4 frontend tests, 16 browser journeys,
PostgreSQL integration, exact restore digests for 11 disposable CI tables,
format/lint/types, package/build and security checks. Final deployed commit
`3f29a6ad3ae33ad490f55080b08fde5761953707` also passed all beta gates in
[run 35513784253](https://github.com/lupu-spec/Landwolf/actions/runs/35513784253).
The commands are the canonical beta commands documented in the earlier successful
run and `beta/AGENTS.md`; each completed with exit 0 in these hosted jobs.

Render deployment `dep-danu0kjtqb8s73d5i2j0` became **live** at 13:32:51 UTC.
Observed application logs report schema v4 ready, successful application startup,
and listening on `0.0.0.0:10000`. The subsequent error-level log query returned no
entries for the period beginning 13:32:46 UTC. Production remained on its prior
live deployment `dep-dangjc142hec73eebq10`, commit `5f651785...`, when rechecked.

#### Hosted verification

[Run 35513842562](https://github.com/lupu-spec/Landwolf/actions/runs/35513842562),
job `106086314948`, ran `.venv/bin/python scripts/check_hosted_staging.py`
successfully (exit 0) against the actual deployed service. The check source is in
commit `92f6db0d91028b9ca695c391d945a4053015e10d`; that follow-up adds test tooling,
not a different deployed app runtime. Passed:

- HTTPS health and schema/database readiness; environment is staging; payments
  and outbound email disabled; `noindex`; unauthenticated sources/capabilities/
  search rejected; retired Saved endpoint absent.
- Four Chromium/WebKit journeys at 390px and 1440px: registration/sign-in,
  real inventory, property evidence, Research context handoff, county coverage,
  session persistence across reload and sign-out. Page/dialog overflow assertions
  and uncaught-browser-error checks passed.
- An authenticated live reference-research request at 35.7804, -78.6391 returned
  five sources with overall status `ready`. Missing-CSRF search was rejected.
- Seven inventory feeds reported ready: Minnesota DOT, Arkansas COSL, Texas GLO,
  USDA, Treasury, Alaska DNR and Michigan DNR. IRS reported unavailable. This is
  observed retrieval status, not a guarantee of data correctness or nationwide coverage.

The workflow installed locked dependencies with `uv sync --frozen --dev` and
`.venv/bin/playwright install --with-deps chromium webkit`, and ran Ruff format/lint
on the smoke script, all successfully. Artifact `10606540567` contains 16 screenshots
with seven-day retention. Downloaded archive via `curl` (exit 0) and visually
inspected mobile WebKit Explore/Coverage and desktop Chromium property evidence.
Labels, navigation, filters and evidence were readable with no clipped page width.
The observed Explore screen showed 510 active results. One disposable account with
a generated password and reserved example.com address remains in staging; no user
accounts were copied, and credentials/session state were not saved in artifacts.

#### Local command evidence and limitations

- **Passed:** `uv sync --frozen --dev`; repaired a stale local environment whose
  missing interpreter caused the initial `.venv/bin/pytest` invocation to exit 127.
- **Passed:** `.venv/bin/ruff format --check landwolf tests scripts`,
  `.venv/bin/ruff check landwolf tests scripts`,
  `.venv/bin/pytest -q tests/test_staging_startup.py` (3 passed), and
  `/bin/sh -n landwolf/start_staging.sh`, exit 0.
- **Passed:** both revised Blueprints against the cached official Render schema
  using the same isolated JSON Schema validation command above; Prettier checks
  for those YAML files and `.github/workflows/staging-smoke.yml`; configured
  Secretlint scans of all new/changed scripts, tests and configuration; diff checks.
- **Passed:** Ruff format/lint and Python compilation of `check_hosted_staging.py`.
  Initial lint caught a callback loop binding and line length; a follow-up format
  check caught print wrapping. These were corrected before publishing/running it.
- **Failed preliminary secret scan:** running Secretlint from the repository root
  could not find the beta config. Re-running from `beta/` succeeded; the original
  shell's trailing successful diff check did not make that scan a pass.
- **Passed:** `curl --fail --silent --show-error --max-time 45
  https://landwolf-premium-staging.onrender.com/api/health`, exit 0, returned
  `{"status":"ok","version":"0.2.0","payments_enabled":false}`. Earlier 30-second
  request during the failed startup timed out with curl exit 28.
- **Unavailable:** direct database inspection through Render's read-only query
  connector failed with EOF/TLS errors. External database access remains blocked;
  successful application health and hosted authenticated journeys establish the
  internal application/database path, not successful connector access.
- **Not run:** real email delivery, physical-device tests, a full accessibility
  audit, or restoration of a staging/production snapshot. Disposable CI restore
  success is not a completed restore of this hosted database. These remain gates
  before production promotion; the free web service can sleep and pause refreshes.
- **Blocked optional setting:** automatic approval review rejected changing
  Blueprint Auto Sync from Yes to No, stating future synchronization changes were
  outside the deployment approval. The edit was cancelled. Service auto-deploy
  is off, but linked Blueprint edits can still sync automatically.

No production deployment, domain, payment, account migration or database deletion
was performed. IRS availability and separate legacy workflow failures remain open.

## Versioned release and maximum-bid display removal — September 21, 2026

Owner requested promotion of the premium beta to `landwolf.ai`, a production/beta
version ledger, and removal of the navy Model Maximum Bid card while keeping the
three white simulation metrics. Runtime candidate `f96208d897dc22c48f685237eb9477ba1c0b9aa8`
is v0.3.1. It retains median net profit, probability of loss and median ROI, with
three desktop columns and one mobile column. Maximum-bid display/copy is removed;
the existing API field remains for compatibility. Logo, free access, authentication,
scenario assumptions and permanent Saved removal are unchanged.

Versioned v0.3.0 introduced `/api/version` (version, environment, validated commit),
a footer link to `RELEASES.md`, consistent package versions and version regression
checks. It was deployed only to staging, commit
`a8157056090bb39138d334da2eeb7ae59555abe9`, deployment
`dep-danudomk1f9s73a0jvu0`, live September 20 at 14:01:02 UTC.
All release gates passed in [run 35514939265](https://github.com/lupu-spec/Landwolf/actions/runs/35514939265).
Hosted checks first failed waiting five seconds for property cards immediately
after startup. The unchanged warmed service passed all four journeys on retry,
job `106089989694`, [run 35514939253](https://github.com/lupu-spec/Landwolf/actions/runs/35514939253).
The v0.3.1 hosted check now allows 45 seconds for assertions on the free staging
service and additionally verifies the three-card simulation in both browsers.

### Recovery evidence

Render production recovery has a three-day PITR window. Logical exports from
September 20 13:48 UTC and September 21 13:32 UTC were observed available; Render
states at least seven days' export retention. This is not an off-provider backup.

On September 21, the actual September 20 13:50 UTC staging export was restored
into a freshly named logical database on the existing staging PostgreSQL instance.
No paid instance, network allowlist, production database or customer password was
changed. PostgreSQL 18 `pg_restore` supplied pre/post schema SQL; Psycopg COPY
restored the archive table payloads. Every row matched across all 11 tables.
Snapshot SHA-256: `a71868fd2128b36090c416e12b310ce96994aaad06bff3cc7df48a5cab5357ac`.
The v0.3.0 app then passed sign-in, inventory search and field-evidence queries
against that restored database. Only a disposable `@example.com` account in the
restored copy received a temporary password, after row comparison; no production
or staging account was changed. The temporary database was dropped afterward.
Earlier rehearsal attempts caught an archive terminator mismatch, an empty
credential field and selection of a non-test account; each stopped safely and
any created temporary database was cleaned up. Final rehearsal passed.

A credential-hash checkpoint was rejected by automatic safety review as unnecessary
credential access. The safer production checkpoint reads only account IDs/counts
and schema version: 14 accounts, schema v3, ID-set digest
`22a39fc295ebee288736414b68fc0e5b0674931e48a3c884e1872205767f4ccf` before migration.
An old schema-v3 image cannot serve schema v4. Rollback requires coordinated data
restoration/reconciliation; prefer a tested fix forward. Existing accounts must
remain intact during the additive migration.

### Local v0.3.1 commands

| Command from `beta/` | Result |
| --- | --- |
| `npm run format` | Passed; formatting applied and diff reviewed. |
| `.venv/bin/ruff format --check landwolf tests scripts` | Passed before hosted-smoke edit; final full check delegated to CI. |
| `.venv/bin/ruff format landwolf tests scripts` | Passed after final code edits. |
| `.venv/bin/ruff check landwolf tests scripts` | Passed. |
| `npm run lint` | Passed. |
| `.venv/bin/mypy landwolf` | Failed: local internal cache error. |
| `.venv/bin/mypy --cache-dir=/tmp/landwolf-v031-mypy landwolf` | Passed, 21 source files. |
| `npm run typecheck` | Passed. |
| `npm run test:unit` | Passed, four tests. |
| `.venv/bin/pytest -q -m 'not browser'` | Passed, 275 tests; 16 browser tests belong to their separate gate. |
| `git diff --check` and `git status --short` (repository root) | Passed; only intended release changes. |

After session resumption, an initial local pytest invocation failed because the
transient Python interpreter had disappeared. `uv sync --frozen --dev` restored
the locked environment and `.venv/bin/pytest -q tests/test_version.py` passed all
seven version tests. A local direct HTTPS check previously timed out; it was not
counted as a pass. Hosted checks supply actual HTTPS/browser evidence.

Email remains disabled in the owner's requested free release; actual sender setup
and delivery are not verified and remain prerequisites to enabling that feature.
No billing, partner delivery or licensed valuation service is activated. IRS
inventory remains unavailable; public data coverage is partial. Physical devices
and a complete accessibility audit were not tested. Legacy root workflows still
fail independently and are not reported as passing release checks.

### v0.3.1 hosted release gates

[Run 35615851635](https://github.com/lupu-spec/Landwolf/actions/runs/35615851635),
job `106386238990`, passed on the exact runtime commit. Commands actually run:
`uv sync --frozen --dev`, `npm ci`, Playwright installation;
`ruff format --check landwolf tests scripts`, `npm run format:check`;
`ruff check landwolf tests scripts`, `npm run lint`; `mypy landwolf`,
`npm run typecheck`; `npm run test:unit`; `pytest -q -m 'not browser'`;
`python scripts/check_postgres.py`; `python scripts/check_restore.py`;
`npm run build`; `pytest -q -m browser`; `python -m build`;
`python scripts/check_package.py`; `bandit -r landwolf`;
`pip-audit --local --skip-editable`; `npm audit --audit-level=moderate`;
`npm run secrets`; `git diff --check`; `git status --short`.
Python commands used `.venv/bin/` and succeeded. Result: 275 backend tests,
four frontend tests, 16 browser journeys, disposable PostgreSQL migration/restore,
build/package and security checks passed.

Staging deployment `dep-daokckdg1s2s738nf7c0` became live September 21 at
15:00:38 UTC. [Hosted run 35615851629](https://github.com/lupu-spec/Landwolf/actions/runs/35615851629),
job `106386238816`, passed the exact version/commit check, authentication/CSRF,
property evidence, three-card simulation, Research handoff, coverage, session
persistence/logout and no horizontal overflow in Chromium/WebKit at 390/1440px.
Live reference research returned ready. IRS remained unavailable; GLO/USDA were
refreshing at observation. Screenshot artifact `10645968080` was produced, but
local download returned HTTP 403, so those images were not visually reviewed here.

### Production observation

Render deployed the same v0.3.1 commit as `dep-daokek0ae00c73csh0ag`, live
September 21 at 15:05:01 UTC. The 14 pre-existing account IDs have the same
SHA-256 digest after the additive schema v3→v4 migration. The read-only post-check
excluded later-created accounts using `created_at <= 1790002864`; it read no
passwords or password hashes. No account reset, database replacement, billing
activation or DNS change occurred.

The first hosted production smoke attempt, job `106387968931`, observed the exact
version endpoint but then received HTTP 502 from `/api/health` during startup.
It failed, and the same job was rerun. Render's warning/error log query separately
returned a provider-side 503/502, so an error-free log scan is not verified.


The production rerun passed at 15:09 UTC: [run 35616356656](https://github.com/lupu-spec/Landwolf/actions/runs/35616356656),
job `106389452546`, executed `.venv/bin/python scripts/check_hosted_staging.py
--environment production`. It verified the exact runtime version/commit, HTTPS,
www redirect, disabled billing/mail, authentication/CSRF, live research, property
evidence, Research handoff, session persistence/logout, and coverage. All four
Chromium/WebKit journeys at 390/1440px passed, including the three white simulation
metrics, absence of Maximum Bid copy and horizontal-overflow checks. One disposable
test account was retained. Screenshots were generated but not visually reviewed.
An internal Render-shell HTTP check also returned 200 with version 0.3.1 from
both localhost and https://landwolf.ai/api/health. The independent production
release-gate [run 35616356560](https://github.com/lupu-spec/Landwolf/actions/runs/35616356560),
job `106387968985`, passed the same full command suite listed above.


## Hunt save durability repair — candidate v0.4.0-beta.5

Scope: isolated staging only; production and schema v5 remain unchanged.
The direct staging API probe on v0.4.0-beta.4 passed all five acreage bands,
POST 201, GET read-back, edit, fresh-login persistence, matching and cleanup.
Evidence: GitHub Actions run 36506203222. The earlier visual agent report lacked
network evidence and is not accepted as proof of failed persistence.

Local fault injection reproduced the defect before modification: malformed listing
validation and matching exceptions aborted the save (three failing regressions).
Preferences now commit before the independent matching transaction. Match errors
return a saved ID with an explicit unavailable status, not a false zero-match claim.
Database insert errors still return failure. UI confirmation requires the saved ID
in the refreshed account list; matching retry and visible save feedback are separate.

Local `PYTHONPATH=. pytest -q tests/test_hunt.py tests/test_hunt_save.py --tb=short`
passed 11 tests using the available Python environment, not the pinned CI environment.
Added PostgreSQL durability coverage and Chromium/WebKit failure/retry/reload cases.
Pinned format, lint, type, complete tests, build, security and deployment checks are
pending hosted execution; this entry does not claim a deployed fix.

## Investor feedback pilot — candidate v0.4.0-beta.7 (2026-10-04)

Built on `codex/billing-exemptions-admin` at `db65198`. No deployment was performed.
Adds schema-v7 investor invitations, explicit consent, fixed three-calendar-month
terms, scheduled required feedback, owner reporting and server-side cohort gates.
Existing non-cohort access and disabled payments remain unchanged. Reminder polls
do not extend idle login sessions. See `INVESTOR_PILOT.md` for the contract.

Commands below run from `beta/` unless identified otherwise. Final local results:

| Command | Result |
| --- | --- |
| `uv sync --frozen --dev` | Passed, exit 0 |
| `uv lock --check` | Passed, exit 0 |
| `npm ci` | Passed, exit 0 |
| `.venv/bin/ruff format --check landwolf tests scripts` | Passed, exit 0 |
| `npm run format:check` | Passed, exit 0 |
| `.venv/bin/ruff check landwolf tests scripts` | Passed, exit 0 |
| `npm run lint` | Passed, exit 0 |
| `.venv/bin/mypy landwolf` | Passed, exit 0; 24 modules |
| `npm run typecheck` | Passed, exit 0 |
| `npm run test:unit` | Passed, exit 0; 9 tests |
| `.venv/bin/pytest -q -m 'not browser'` | Passed, exit 0; 315 tests, 28 browser cases deliberately excluded from this command |
| `PYTHONPATH=. .venv-legacy/bin/pytest -q` (repository root; separately installed root requirements) | Passed, exit 0; 53 legacy tests |
| `npm run build` | Passed, exit 0 |
| `.venv/bin/playwright install chromium webkit` | Failed, exit 1; downloaded browser archive was invalid/unavailable |
| `.venv/bin/pytest -q -m browser --maxfail=1` | Failed, exit 1 before first browser launch; Chromium executable unavailable. Browser behavior is NOT verified. |
| `.venv/bin/python scripts/check_postgres.py` | Not run: no disposable `landwolf_ci` PostgreSQL service in this workspace |
| `.venv/bin/python scripts/check_restore.py` | Not run: no disposable PostgreSQL service/container |
| `.venv/bin/python -m build` | Passed, exit 0; candidate source archive and wheel built |
| `.venv/bin/python scripts/check_package.py` | Passed, exit 0 |
| `.venv/bin/bandit -q -r landwolf` | Passed, exit 0 |
| `.venv/bin/pip-audit --local --skip-editable` | Passed, exit 0; no known vulnerabilities, editable project excluded as specified |
| `npm audit --audit-level=moderate` | Passed, exit 0; zero vulnerabilities |
| `npm run secrets` | Passed, exit 0 |
| `git diff --check` (root) | Passed, exit 0 |
| `git status --short` (root) | Passed, exit 0; intended candidate modifications reviewed |

Earlier failures resolved: two new test assertions expected 404 for unauthorized
unenrolled acceptance; the explicit invitation authorization contract returns 403,
and the assertions were corrected to match that contract. Ruff import ordering
was corrected. Existing dependency findings were repaired with compatible locked
transitive updates only: brace-expansion 5.0.9→5.0.12, fast-uri 3.1.7→3.1.8,
urllib3 2.7.0→2.8.0. No audit rules or test gates were weakened.

Security review: response ownership comes from the authenticated session; no body
can select another account. Owner APIs require the immutable configured owner ID.
Writes retain origin/CSRF checks, strict bounded payloads, transaction rollback,
and replay constraints. Submitted feedback uses text nodes in the browser. No
secrets, production records, external messages, account grants or payments were
created. Two feedback browser journeys are committed for CI, but not claimed passed.

Release blockers: complete hosted browser and disposable PostgreSQL/restore gates;
confirm the intended Render workspace and current deployed source branch; inspect
existing owner-account configuration; then migrate and verify the exact live version,
commit, HTTPS, consent/survey flow and account continuity. Public endpoint attempts
from this environment returned an intermediary 'Site Unavailable' HTML response,
not application health JSON; this does not establish a production outage.


## 2026-10-04 — investor pilot released to staging and production

Version `0.4.0-beta.7`, runtime `4f52057d6499d420f6cfce6a9e97b1baa29d0dfe`.
All required hosted gates and eight deployed browser journeys passed. Render
reported staging `dep-db1alfh42hec73epuo7g` live at 19:37:40 UTC and production
`dep-db1amtou01pc73djnmm0` live at 19:40:41 UTC. Both reported schema v7 ready.
See [the complete release record](INVESTOR_PILOT_RELEASE.md) for commands, exact
evidence, resolved failures, backup scope, partial source coverage, and unexercised
live owner/investor operations. Earlier candidate limitations above are historical;
they were not counted as passing checks.

## Live billing candidate — 2026-10-04

- Passed: `python -m compileall -q beta/landwolf`.
- Passed before subsequent browser/docs/hardening additions: targeted local pytest
  run of live billing, feedback, admin, config and security: 93 passed. The local
  interpreter is Python 3.13.5 with preinstalled dependencies, not the locked CI
  environment. Re-run final candidate gates before release.
- Live Stripe account: charges and payouts enabled, no current requirements.
  Existing live recurring prices verified: $29/month and $299/year. No live
  subscriptions existed at inspection. Customer portal configured for cancellation
  at period end, invoices and payment-method updates; no charge was made.
- Production deployment, secure runtime keys, live Checkout and genuine webhook
  delivery: NOT VERIFIED. Render browser authentication expired. The read-only
  database connector cannot connect because the production database correctly
  blocks external connections; its network policy was not weakened.

## v0.4.2 source recovery and production wording — candidate

Baseline: live Render commit `baf4c1ffdd26710271dec6575d2442a877b1c4ac`.
The staging branch has no commits ahead of this baseline; its completed features
are already included. No unfinished valuation, partner or parcel integration is enabled.

Changes: handle MnDOT's explicit empty bid section without crossing into unrelated
links; exclude Treasury's undated teasers without sale IDs; exclude IRS cards marked
as external-sale promotions. Retain URL restrictions, bounded retrieval, source
provenance and snapshot quarantine. Remove obsolete product labels from UI/status/
model copy; correct current feature documentation. Infrastructure names and historical
release records retain their existing identifiers. No schema/dependency changes.

The baseline browser test contained literal backslash-n characters at the annual-plan
selection step and could not parse. Corrected to actual line breaks. Baseline billing
Python/TypeScript also required formatting; the Python billing AST is unchanged.
No billing settings, prices, provider API contracts, entitlement or payment logic changed.

Passed locally (exit 0): locked `uv sync --frozen --dev` and `npm ci`; ruff/prettier
format checks; ruff/eslint; mypy/TypeScript; 9 frontend tests; 364 non-browser tests;
`npm run build`; `git diff --check`. Initial mypy failure for the new BeautifulSoup
class access was fixed with its typed attribute-list API before these passes.

Actual `python -m landwolf.cli sync` against a fresh disposable SQLite database
passed (exit 0): MN 4, AR 0, TX 31, USDA 19, Treasury 19, IRS 1, AK 170, MI 28.
These are retrieved records, not a claim of every record being current/eligible for search.
Zero Arkansas records is a successfully parsed upcoming-sale catalog, not an outage.

Public research checks at Dallas and Raleigh returned partial (exit 1): Census,
USGS, soils and applicable NC parcels returned evidence; FEMA's reviewed endpoint
returned HTTP 502 on both layers. Its findings remain unknown. No fabricated fallback.

Local Playwright browser installation failed: downloaded browser archives were invalid.
Hosted CI must provide Chromium/WebKit, disposable PostgreSQL and restore verification
before promotion. The direct landwolf.ai checks returned a generic Site Unavailable
page from this execution session; this is not evidence of application-wide downtime.

Daily source-maintenance automation was created for mornings around 08:00
America/Chicago. It checks current production, repairs confirmed source changes,
requires repository gates, preserves billing and quarantine, and reports unresolved
provider/authentication failures. The existing six-hour catalog scheduler remains.

Production deployment and hosted verification are pending; a branch is not a deployment.

Hosted run 37262751984 passed format, lint, types, 364 API/unit tests, PostgreSQL
integration and disposable backup/restore. Browser results: 22 passed, 8 failed
because the roadmap CSS selectors were renamed without updating the browser tests.
Corrected the selectors without changing their assertions. Full rerun required.
Additional local passes: package build/check; bandit; pip-audit; npm audit;
secretlint; `uv lock --check`; 53 legacy tests in the separate environment.
