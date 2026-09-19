# LandWolf beta verification

The free beta is live at **https://landwolf-free-beta.onrender.com/** on runtime
commit `f9b0fcc7711db0b8df0a968575775139b79ad580`. The latest deployed checks
completed on September 14, 2026, at 16:15:59 UTC; see the final deployment section.

The initial local results below were observed on September 14, 2026, on branch
`codex/landwolf-beta-rebuild`, based on
`5307de0a11fd75a7c51bdf5243f3e13179b95d38`. Python 3.12 and Node 24 were used
with committed dependency locks. Historical results are retained with their scope.

## Changes

- Original owner-supplied logo and navy/white identity; responsive sign-in,
  property discovery, map/list views, details, saved properties, and analysis.
- Fresh accounts, server-enforced authentication before property queries, hashed
  opaque sessions, ownership checks, CSRF protection, and disabled payments.
- An official Texas GLO public-sale connector with independent inventory/detail
  freshness, validated source coordinates, bounded requests, and cache retention
  on upstream failure. Overlapping map pins expose every grouped property.
- Explicit cost/resale inputs and reproducible 10,000-scenario risk, profit,
  median ROI, and maximum-bid calculations with stated model limitations.
- Enforceable root and beta `AGENTS.md` policies, isolated CI, a packaged frontend,
  and a separate Render service/database configuration with automatic deploys off.
- All pre-existing application files and production configuration remain unchanged.

## Commands and observed results

Commands below run from `beta/` unless another directory is stated. **Passed**
means the command completed with exit status 0. Browser environment prefixes are
listed separately so the actual browser execution can be reproduced accurately.

| Command | Result | Evidence and scope |
| --- | --- | --- |
| `uv sync --frozen --dev` | **Passed** | Installed the locked isolated Python environment. |
| `uv lock --check` | **Passed** | Python lock matches project metadata. |
| `npm ci --no-fund` | **Passed** | Clean installation from the committed Node lock. |
| `.venv/bin/ruff format --check landwolf tests scripts` | **Passed** | 17 files formatted. |
| `npm run format:check` | **Passed** | Configured frontend/build files formatted. |
| `.venv/bin/ruff check landwolf tests scripts` | **Passed** | No lint findings. |
| `npm run lint` | **Passed** | ESLint completed successfully. |
| `.venv/bin/mypy landwolf` | **Passed** | Strict checking of 10 source files. |
| `npm run typecheck` | **Passed** | TypeScript completed without emitting files. |
| `.venv/bin/pytest -q -m 'not browser'` | **Passed** | 64 tests; browser test deliberately belongs to the next gate. |
| `npm run build` | **Passed** | Built browser bundle, styles, Leaflet, and branding assets. |
| `.venv/bin/pytest -q -m browser` with fixture prefix below | **Passed** | One complete real Chromium journey using an isolated database and synthetic source fixtures. |
| `.venv/bin/python -m landwolf.cli sync` | **Passed** | Official upstream returned 29 active records; status ready, stale false; successful retrieval at 2026-09-14 09:53:48 UTC. All 29 have source detail data and coordinates. |
| `.venv/bin/pytest -q -m browser` with live prefix below | **Passed** | Complete browser journey over those 29 source records; real source photo and OSM tile loading explicitly asserted. Latest run: 1 passed, 64 deselected, 26.28 seconds. |
| `.venv/bin/python -m build` | **Passed** | Built source archive and application wheel. |
| `.venv/bin/python scripts/check_package.py` | **Passed** | Wheel includes the app, HTML, JavaScript, styles, Leaflet, exact logo, and landscape. |
| `.venv/bin/bandit -r landwolf` | **Passed** | No static security findings. |
| `.venv/bin/pip-audit --local --skip-editable` | **Passed** | No known vulnerabilities reported in installed dependencies. The local editable app is covered by source analysis and tests, not an advisory database. |
| `npm audit --audit-level=moderate` | **Passed** | Zero reported vulnerabilities. |
| `npm run secrets` | **Passed** | Configured masked secret scan over new code, fixtures, docs, policy, workflow, and deployment file. |
| `git diff --check` (repository root) | **Passed** | No whitespace errors after correcting an extra favicon EOF newline. |
| `git status --short` (repository root) | **Passed** | Only new beta, policy, workflow, and beta deployment files. |

Fixture browser prefix:

```sh
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/workspace/scratch/bae2278276c6/browser-tools/chromium
```

Live browser prefix (all three assignments apply to the same pytest command):

```sh
LANDWOLF_BROWSER_PROXY=1 LANDWOLF_E2E_LIVE=1 PLAYWRIGHT_CHROMIUM_EXECUTABLE=/workspace/scratch/bae2278276c6/browser-tools/chromium
```

The browser is Chromium 153.0.8010.0, obtained from `@sparticuz/chromium@153.0.0`.
The live run uses the workspace's supplied proxy and its CA, imported into the
browser's NSS trust store for that execution. TLS verification and the app's CSP
remain enabled. The server and browser run in one process tree because this
workspace isolates network access between command sessions. CI uses Playwright's
normal Chromium installer instead. The subsequently observed hosted CI results are recorded below.

The browser journey covers pre-login search concealment, account creation,
authenticated search, grouped map selection, list/map/split modes, an uncovered
state, saving, property/source details, analysis, invalidating results after input
changes (including an in-flight response), 390px mobile layout, session reload,
logout, cleared private UI, empty local storage, and absence of JavaScript errors
or failed application API responses. API tests separately cover unauthorized
access, save ownership, session/CSRF/origin checks, rate limits, malformed input,
source failures, and model invariants. These tests do not certify security.

Additional executed checks:

- **Passed:** the Render file validated against the downloaded official
  `https://render.com/schema/render.yaml.json` using Python's
  `jsonschema.Draft202012Validator` and `yaml.safe_load`, run with
  `uv run --isolated --with jsonschema --with pyyaml python` and the validator
  script on standard input. The YAML value `autoDeployTrigger: "off"` is quoted
  to preserve its required string type.
- **Passed:** Python `hashlib.sha256` equality check between the supplied original
  logo and `web/assets/landwolf-logo.png`.
- **Passed:** visual inspection of the login, desktop discovery, analysis, and
  mobile screenshots. The analysis screenshot uses explicitly synthetic investor
  assumptions; its return figures are not an assessment of the displayed tract.

## Failed attempts, resolutions, and unavailable gates

| Command/check | Result | Explanation |
| --- | --- | --- |
| Initial dependency audit with pytest 8.4.2 | **Failed**, resolved | Advisory PYSEC-2026-1845 was reported. Updated the beta test dependency to 9.0.3, regenerated locks, and reran the test suite and clean audit. |
| `npx agent-browser install` | **Failed** | Browser download could not validate the environment's certificate chain. |
| `.venv/bin/playwright install chromium` | **Failed** | Browser download timed out; no success is claimed for that installer. The separately obtained Chromium executable ran the actual Playwright tests successfully. |
| Agent-browser session startup | **Failed** | The environment rejected its Unix daemon socket with `Operation not permitted`. Used Playwright directly; agent-browser itself is not verified. |
| Initial live browser attempts | **Failed**, resolved | External assets failed without the workspace proxy/CA. The final run asserts actual image and tile dimensions with TLS verification retained. |
| Legacy `/workspace/scratch/bae2278276c6/legacy-venv/bin/pytest -q` (repository root) | **Failed** | Initial collection could not import `investment_engine` with that external environment's launcher. |
| Legacy `PYTHONPATH=. /workspace/scratch/bae2278276c6/legacy-venv/bin/pytest -q` (repository root) | **Failed** | 48 passed, 5 failed because legacy `.env.sandbox.example` and `.env.live.example` fixtures are absent. No legacy tests or implementation files were changed. |
| `docker build -f beta/Dockerfile beta` (repository root) | **Not run** | Docker is not installed in this workspace. Wheel validation is not a container build. |
| Production PostgreSQL integration | **Passed** | New PostgreSQL 18 database; observed schema bootstrap, health query, account creation, idempotent saves, ownership isolation, and save persistence across login. See final deployment evidence. |
| Deployed HTTPS health, session APIs, public login screen, and live refresh | **Passed** | Actual HTTPS service, 29 fresh official records, original branding, and authenticated API journey verified. |
| Authenticated browser journey on the deployed service | **Not run** | The deployed authenticated journey was tested through HTTP APIs. The complete browser journey passed in hosted CI against its isolated fixture server; the deployed public login page was inspected separately. |
| `git push -u origin codex/landwolf-beta-rebuild` | **Failed**, publication resolved | Initial automatic review required explicit destination authorization. After the owner approved, the shell attempt failed because Git had no login. The authorized GitHub connector then published the exact reviewed tree, verified by its tree and asset hashes. |
| Draft pull request | **Passed** | [PR #1](https://github.com/lupu-spec/Landwolf/pull/1) is open as a draft; no merge occurred. |

The five unchanged legacy failures are in `test_landwolf_domain_billing.py`,
`test_live_stripe_connected_ids.py`, two cases in
`test_live_stripe_deployment_kit.py`, and `test_stripe_plan_checkout.py`.
Pytest also emits two third-party deprecation warnings from Starlette's current
TestClient/httpx integration and AnyIO's `BlockingPortal` alias. They are not suppressed.


## Published source and hosted CI

The owner explicitly approved publishing this rebuild to `lupu-spec/Landwolf`
and deploying a separate paid beta in Render's **My Workspace**. That approval
remains in effect. The source was published in commit
`e6c741faef1ed8368592c1b16e4bcde6c73c1cf1`; its complete tree hash,
`d52f8270659395eaf63ff468627747894bf1cc40`, exactly matches the reviewed local
tree. All six binary assets were also checked against their Git blob hashes.

The following hosted results were observed through GitHub's workflow and job APIs.
They apply to that source commit; this later report update changes documentation only.

| Hosted workflow/check | Result | Observed evidence |
| --- | --- | --- |
| [LandWolf beta gates, run 34839910064](https://github.com/lupu-spec/Landwolf/actions/runs/34839910064) | **Passed** | Job `verify` completed successfully. Locked installation, formatting, lint, types, unit/API tests, browser journey, production package, security, diff integrity, and screenshot upload all report success. |
| Legacy Test, run 34839910053 | **Failed** | Its unchanged root test environment stops during collection with `ModuleNotFoundError: No module named 'investment_engine'`. This is distinct from the five fixture failures observed locally with `PYTHONPATH=.`. |
| Legacy Release Preflight, run 34839910038 | **Failed** | Its unchanged static preflight job installs pytest without the dependencies imported by the root test configuration and stops with `ModuleNotFoundError: No module named 'numpy'`. Production/staging preflight jobs were skipped, not passed. |
| Render beta provisioning and deployed verification | **Passed** | Separate beta service and database created. Deploy `dep-dak1oqe7bikc739nj210` is live at runtime commit `f9b0fcc7711db0b8df0a968575775139b79ad580`; scope and limits appear below. |

The existing Render app and database were inspected without modification. These
initial CI results preceded deployment. The later container and hosted checks
below establish deployment separately; CI success alone is not deployment evidence.

### Earlier Render dashboard continuation — September 14, 2026

- The earlier workspace connection and Render sign-in blockers are resolved.
  Fresh Render dashboard evidence shows the approved **My Workspace**.
- Prepared Blueprint name `landwolf-free-beta`, repository `lupu-spec/Landwolf`,
  branch `codex/landwolf-beta-rebuild`, and path `render.beta.yaml`.
- Render displayed **Payment Information Required** before resource creation.
  The workspace billing page separately reports **No card on file**. The owner
  must add a payment method directly in Render; no card data belongs in this repo.
- After billing is ready, resume this existing form, review the two new beta
  resources and plans, configure the actual generated HTTPS origin, deploy,
  and run the outstanding hosted checks. Do not deploy the legacy `render.yaml`.
- This continuation changes only this status report; no application code changed.
- Documentation checks: `npm run secrets` from `beta/`, `git diff --check`, and
  `git status --short` from the repository root all exited 0. Only this report
  changed. Application test suites were not rerun for this documentation update.

### Render origin correction — September 14, 2026

The owner added a payment card. Render then displayed the intended create plan:
`landwolf-free-beta` on `starter` and `landwolf-beta-db` on `basic-256mb`.
Automatic approval review rejected submitting a temporary `pending.invalid` origin;
that rejected action created no resources. The revised Blueprint has no placeholder
or manually required origin. The app uses Render's documented
[`RENDER_EXTERNAL_URL`](https://render.com/docs/environment-variables) only when
`RENDER=true`, validates the assigned HTTPS `onrender.com` origin, and stops startup
on invalid or missing platform configuration. An explicit `LANDWOLF_PUBLIC_ORIGIN`
override still takes precedence and must pass validation. Host headers never choose
the security boundary.

Changed `landwolf/config.py`, `tests/test_config.py`, `README.md`, and the root
`render.beta.yaml`. Sixteen additional cases cover platform URL validation,
configuration precedence, development behavior, and actual host/CSRF/cookie behavior.
The source connector, model, UI, original branding, and legacy app are unchanged.

Commands below ran after this source change. Except where stated, the directory
is `beta/`; successful commands exited 0.

| Command | Result | Evidence |
| --- | --- | --- |
| `uv sync --frozen --dev` | **Passed** | Restored the locked environment after its interpreter link was lost. |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | **Passed** | 18 Python files and configured frontend files formatted. |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | **Passed** | No lint findings. |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | **Passed** | Python strict types and TypeScript checks passed. The initial mypy attempt exited 127 before the environment restoration; the retry exited 0. |
| `.venv/bin/pytest -q -m 'not browser'` | **Passed** | 80 passed, 1 browser test deselected, 2 existing deprecation warnings. |
| `npm run build` | **Passed** | Browser assets built. |
| `PLAYWRIGHT_CHROMIUM_EXECUTABLE=/workspace/scratch/bae2278276c6/browser-tools/chromium .venv/bin/pytest -q -m browser` | **Failed** | Chromium exited with SIGSEGV at launch; the UI journey did not start. Await the hosted browser gate for this source revision. |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | **Passed** | Source archive and wheel built; required application and original branding assets present. |
| `.venv/bin/bandit -r landwolf` | **Passed** | No findings. |
| `.venv/bin/pip-audit --local --skip-editable`; `npm audit --audit-level=moderate`; `npm run secrets` | **Passed** | No known dependency vulnerabilities or secret-scan findings. |
| `uv run --no-project --isolated --with jsonschema --with pyyaml python` with the schema-validation script on stdin (root) | **Passed** | Revised Blueprint validates against the official cached Render schema. The earlier attempt without `--no-project` failed while trying to build the unchanged legacy root package. |
| `PYTHONPATH=. /workspace/scratch/bae2278276c6/legacy-venv/bin/pytest -q` (root) | **Failed** | 48 passed, the same 5 missing legacy environment-fixture failures. |
| `git diff --check`; `git status --short` (root) | **Passed** | Reviewed the isolated configuration, regression tests, and documentation changes. |

The origin correction was published as
`79835e36691a98edce54776f9d514a2af79f18f8`, with remote tree
`bc3350057b231f1c41afcb06b778cae0fe71ad78` matching the reviewed local tree.
[Hosted beta run 34865893100](https://github.com/lupu-spec/Landwolf/actions/runs/34865893100)
passed every step, including its real Chromium browser journey.

## Final deployment — September 14, 2026

Render built the first Docker image successfully. Its pre-deploy command then
failed because `Literal[False]` rejected the environment string `"false"` in
`LANDWOLF_PAYMENTS_ENABLED`. A before-validator now accepts only boolean false or
the explicit case-insensitive string `"false"`; true and ambiguous inputs fail.
Nine new regression cases cover the actual environment path. Payments remain
disabled. This correction is runtime commit
`f9b0fcc7711db0b8df0a968575775139b79ad580`, tree
`cca32280b8165026777467e5ddcbc54c5f69730b`; remote and reviewed local tree hashes
matched before the beta branch was updated.

### Commands after the final source correction

All commands run from `beta/` unless stated otherwise. Each **Passed** command
actually exited 0 after the final application change.

| Command | Result | Evidence |
| --- | --- | --- |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | **Passed** | 18 Python files and configured frontend files formatted. |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | **Passed** | No lint findings. |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | **Passed** | Strict Python checking and TypeScript completed. |
| `.venv/bin/pytest -q -m 'not browser'` | **Passed** | 89 passed, 1 browser test deselected, 2 retained dependency deprecation warnings. |
| `npm run build` | **Passed** | Browser assets built. |
| `.venv/bin/pytest -q -m browser` | **Passed in hosted CI** | The normal Chromium browser journey passed in run 34866716634. Not rerun with the locally crashing browser executable. |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | **Passed** | Source archive, wheel, and required assets validated. |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable`; `npm audit --audit-level=moderate`; `npm run secrets` | **Passed** | No static findings, known dependency vulnerabilities, or secret-scan findings. |
| `git diff --check`; `git status --short` (root) | **Passed** | Only the reviewed configuration and test changes before publication; local tree subsequently matched the published commit. |
| `.venv/bin/python -` with the deployed HTTPS integration script on stdin | **Passed** | Completed at 16:15:59 UTC against the actual beta, with the checks below. |
| Render Docker build using `beta/Dockerfile`, `npm ci --no-fund`, `npm run build`, and `pip install --no-cache-dir --require-hashes -r requirements.lock` | **Passed on Render** | Image built and pushed for the deployed runtime commit. Local Docker remains unavailable. |
| `python -m landwolf.cli init-db` in the Render pre-deploy container | **Passed on Render** | Log reports schema version 1 initialized at 16:10:40 UTC and pre-deploy complete. |
| `python -m landwolf.serve` in the Render runtime | **Passed on Render** | Application startup completed, listening on `0.0.0.0:10000`; deploy reported live at 16:10:54 UTC. |

[Hosted beta run 34866716634](https://github.com/lupu-spec/Landwolf/actions/runs/34866716634),
job `104052263435`, completed every configured gate successfully at the final
runtime commit: locked installation, formatting, lint, types, unit/API tests,
browser journey, package, security, diff integrity, and browser evidence upload.
Unchanged legacy workflows still fail separately; they are not beta gate passes.

### Actual deployed verification

- **Passed:** HTTPS `/api/health` returned 200 with schema/database ready, version
  `0.2.0`, and payments false. HSTS, restrictive script CSP, and API `no-store`
  headers were present.
- **Passed:** SHA-256 equality for the deployed original logo, `app.js`, and
  `styles.css` against the tested local build. A real cloud browser displayed the
  public login page and loaded the original 2172px-wide logo. No horizontal page
  overflow was observed at its 1363px viewport.
- **Passed:** server-side 401 responses before authentication for search, source,
  details, save, unsave, and analysis. New accounts received Secure, HttpOnly,
  SameSite=Strict session cookies. Cross-origin and invalid-CSRF writes returned
  403; unknown search fields returned 422.
- **Passed:** 29 real Texas GLO listings, source status ready and not stale,
  successful refresh at **16:11:21 UTC**, official provenance and published
  coordinates on every returned listing, and enriched property details.
  California correctly reported unsupported coverage and no invented inventory.
- **Passed:** PostgreSQL save idempotency, separation between two accounts, and
  protection against a second account removing the first account's save. Saved
  data survived logout and a new login.
- **Passed:** two identical, seeded 10,000-scenario API calculations; deterministic
  synthetic profit, risk, and maximum-bid invariants matched their expected values.
  These assumptions test the model and do not value the displayed property.
- **Passed:** logout revoked the session, replay was rejected, and the successful
  run removed its saved record and revoked both test sessions. Only synthetic
  `deployment-check-...@example.com` accounts were used; no user accounts or source
  listings were modified and no email was sent.

The first ad hoc deployed-check script stopped on an HTTPX `delete(json=...)`
TypeError. The corrected script used `request('DELETE', ..., json=...)` and passed
the complete journey. Four synthetic test accounts were created across the two
attempts. Cleanup was attempted in the failed run and explicitly verified for the
successful run; test passwords and session tokens were never printed or persisted.

The direct database-query connector could not connect because its client reported
SSL/TLS required and unexpected EOF. No network or TLS protections were weakened.
PostgreSQL integration was instead verified through the actual application's
successful bootstrap, health queries, account writes, and ownership/persistence
checks. A later error-log query returned provider 503/504; no claim is made that
this query found zero errors. Earlier build/startup logs were retrieved successfully.

### Infrastructure and operating limits

- Blueprint `exs-dak1e78ae00c73eneogg`; **Auto Sync: No** was saved and observed.
- Web service `srv-dak1lvh42hec73blur00`, `landwolf-free-beta`, Docker, Oregon,
  starter plan, one instance, auto-deploy off, health path `/api/health`.
- Database `dpg-dak1lih42hec73blthcg-a`, `landwolf-beta-db`, PostgreSQL 18,
  basic-256mb, **15 GB storage**, disk autoscaling off, external IP allowlist empty.
  The approved compute and additional storage/usage charges are now active.
- Final live deploy `dep-dak1oqe7bikc739nj210` serves
  **https://landwolf-free-beta.onrender.com/**. The prior deploy
  `dep-dak1lvp42hec73blus20` failed pre-deploy and is not claimed as successful.
- The workspace is Hobby. Render documents a
  [three-day point-in-time recovery window for paid databases on Hobby](https://render.com/docs/postgresql-backups).
  A backup restore was **not run** and is not verified by this deployment.
- Full browser interaction after sign-in on the deployed service was **not run**.
  That flow passed in CI; actual deployed authentication/search/save/analysis were
  tested through HTTPS APIs, and the public deployed UI was inspected independently.

## Product and deployment limits at the initial Texas release

Live coverage is Texas GLO public-sale inventory only. Other states, county tax
sales, foreclosure feeds, municipal surplus, ownership, liens, flood overlays,
comparables, and independent valuations are not connected. The UI reports these
gaps and source freshness. Published location points are not surveyed boundaries.
Scenario outputs depend on user assumptions and omit correlated market shocks;
see [MODEL.md](MODEL.md). Asking prices never establish resale value.

Email ownership verification and automatic password recovery remain to be added
before broad public enrollment. The deployed beta uses its new PostgreSQL database,
validated Render-assigned HTTPS origin, and one worker/instance. Review longer-term
backup retention and test restoration before broader operation. Hosting charges
apply to the two new beta resources; the existing production service/database and
the main branch were not modified or merged.

Review screenshots: [login](preview-login.png), [property search](preview-explore.png),
[scenario analysis](preview-analysis.png), [mobile](preview-mobile.png).

## Nationwide expansion — September 14, 2026

The expansion adds a source registry, six additional official-source adapters,
independent atomic snapshots, SQL filtering/counting/pagination, all 50 state
selectors and coverage counts, and sale/deadline/eligibility fields. Unknown prices
and acreage remain unknown. Tax balances, government bids, source appraisals,
asking prices and user-supplied resale assumptions remain distinct. Only published
parcel coordinates appear on the map. See [SOURCES.md](SOURCES.md) for source
contracts and the remaining county and pre-foreclosure gaps.

The original logo/theme, authentication boundary, existing beta accounts, model,
payments-disabled policy, Render resources and legacy application are preserved.
No dependency, paid provider, database migration or infrastructure change is needed.
The CI workflow adds a disposable PostgreSQL 18 integration gate to validate the
new JSON filtering and persistence against the deployed database engine.

### Commands after the final expansion changes

All commands ran from `beta/` unless stated otherwise. **Passed** means exit 0.
The local commands below completed after the final security-fixture correction.

| Command | Result | Evidence |
| --- | --- | --- |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | **Passed** | 24 Python files and configured frontend files formatted. |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | **Passed** | No findings. |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | **Passed** | 14 Python modules and TypeScript checked. |
| `.venv/bin/pytest -q -m 'not browser'` | **Passed** | 115 passed, 2 browser tests deselected, 2 retained dependency deprecation warnings. |
| `.venv/bin/python scripts/check_postgres.py` | **Passed in hosted CI** | PostgreSQL 18 authentication, JSON filters, nulls, dates, pagination and saves passed at 17:17:27 UTC. Not run locally; PostgreSQL/Docker unavailable. |
| `npm run build` | **Passed** | Updated browser assets built. |
| `.venv/bin/pytest -q -m browser` | **Passed in hosted CI** | Both Chromium journeys passed at 17:17:38 UTC: existing discovery/model flow and nationwide category/source/unknown-price/deadline/coverage/mobile flow. Not rerun with the locally crashing browser. |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | **Passed** | Source archive/wheel built; app, new modules and original branding assets packaged. |
| `.venv/bin/bandit -r landwolf` | **Passed** | No findings; 2,157 lines scanned, zero security suppressions. |
| `.venv/bin/pip-audit --local --skip-editable`; `npm audit --audit-level=moderate`; `npm run secrets` | **Passed** | No known dependency vulnerabilities or secret-scan findings. |
| `PYTHONPATH=. /workspace/scratch/bae2278276c6/legacy-venv/bin/pytest -q` (root) | **Failed** | 48 passed; the same 5 missing legacy environment-fixture failures. No legacy source or billing tests changed. |
| `.venv/bin/python -m landwolf.cli sync` | **Passed** | Final source refresh exited 0; all seven automated sources ready by 17:13:52 UTC. 2,539 raw records, 2,528 current after date/status filtering, in 19 states. |
| `git diff --check`; `git status --short` (root) | **Passed** | Reviewed only beta code/tests/docs and its CI workflow; no source snapshots, database files, credentials or unrelated changes. |

### Resolved development findings

- Parser tests caught whitespace-sensitive Alaska auction dates and a Michigan
  acreage pattern that accepted a substring of a negative size. Both were fixed
  and their regression cases pass.
- Initial Alaska/Michigan HTTP reads timed out. New adapters now use 30-second
  request timeouts, one bounded transient retry, a 300-second source deadline,
  an 8 MB response bound and at most 240 requests per source refresh.
- USDA's unfiltered search returned an error page. Retrieval now uses each
  advertised state and property type, verifies advertised counts, parses published
  date formats, withholds ambiguous dates, and distinguishes FSA appraisals.
- The secret scanner initially rejected a literal fake Basic Auth URL in an SSRF
  rejection test. The fixture now constructs that invalid URL; the same security
  assertion remains and the scanner has no added exceptions. The complete local
  gate sequence subsequently passed.
- An intermediate source-result inspection attempted to read the redirected JSON
  file while the refresh was still running and failed with JSONDecodeError. This
  inspection is not a successful refresh or a passing gate.

### Published source and hosted gates

Runtime commit `81929160dc4a3d72e679c658a121203938f6d3c7` has tree
`05dd6d246f18a48ca47dc47e7c7b2268024c7cc8`, exactly matching the reviewed staged
local tree before the beta branch was advanced. Fetching that branch and comparing
it with the local working tree exited 0; the working tree was clean afterwards.

[Push run 34873672194](https://github.com/lupu-spec/Landwolf/actions/runs/34873672194),
job `104075467040`, passed every gate at this exact commit. Logs confirm 115 unit/API
tests, the disposable PostgreSQL integration, and both browser journeys passed.
[PR run 34873674813](https://github.com/lupu-spec/Landwolf/actions/runs/34873674813),
job `104075476374`, independently passed every beta gate. Existing legacy workflows
remain separate failures, not beta passes. No main-branch merge was performed.

### Observed deployment and HTTPS verification

Render deploy `dep-dak2p0jm8hqs7396m50g` built the Docker image for the exact runtime
commit above and reported **live at 17:19:39 UTC**. Logs show `python -m landwolf.cli
init-db` completed against the existing beta database, then `python -m landwolf.serve`
started successfully on port 10000. Service auto-deploy remains off. No additional
resources were provisioned and no production/main-branch changes were made.

The temporary release command
`.venv/bin/python /workspace/scratch/bae2278276c6/source-research/check-deployed-national.py`
ran from `beta/` against **https://landwolf-free-beta.onrender.com/** and exited 0.
The complete successful journey finished at **17:21:19 UTC**:

- HTTPS health and payments-disabled status passed. HSTS, restrictive script CSP,
  API no-store, Secure/HttpOnly/SameSite=Strict cookies, origin and CSRF rejection,
  and rejection of unknown state/source values passed.
- Anonymous search, source, detail, save and unsave requests were rejected.
  Deployed logo, JavaScript and CSS SHA-256 hashes matched the tested build.
- All seven automated feeds reported ready and fresh. All 50 states appeared in
  coverage; directory-only entries contributed zero imported records. Search and
  coverage aggregation agreed on **2,528 current records in 19 states**.
- Arkansas state/category/source filters and the last page beyond 500 records
  passed. Tax balances stayed separate from asking prices; records with unknown
  prices were excluded by an explicit maximum-price filter. California returned
  real inventory; Hawaii correctly retained federal-program search support.
- Pre-foreclosure returned no invented records and explicitly reported that no
  nationwide feed is connected. Connected-source results excluded past sale/bid
  dates. Alaska bid deadlines preceded auction dates and had no invented points.
- Tax property details, duplicate save idempotency, saved search and persistence
  across logout/login passed against the deployed PostgreSQL database. The saved
  test record was removed and the successful test session was revoked.

| Source | Current records in deployed search |
| --- | ---: |
| Arkansas COSL county tax-delinquent sales | 2,288 |
| Texas GLO public land | 29 |
| USDA federal foreclosure/REO | 7 |
| U.S. Treasury real-property auctions | 15 |
| IRS real-estate tax-seizure auctions | 10 |
| Alaska DNR | 171 |
| Michigan DNR | 8 |

These are source records, not a deduplicated count of unique properties or proof
that every state/county is covered. USDA retained 18 raw source records; 11 past
or ambiguous sale-date records were excluded from current search. Only the 29 GLO
records have verified source coordinates; new records without coordinates remain
available in the list and details.

The initial deployed-check attempt failed because its assertion expected the
words "not connected" while the API says "No nationwide pre-foreclosure feed is
connected." The assertion was corrected to match that explicit limitation; no app
code or gate was weakened. The failed attempt had not saved a property and its
session was revoked. Its cleanup message incorrectly said a record was removed;
the temporary script now distinguishes no record created from a successful removal.
Two synthetic `national-deployment-check-...@example.com` accounts were created
across both attempts. Passwords/tokens were neither printed nor persisted; no email
was sent and no real user account or source listing was modified.

A controlled cloud browser loaded the deployed public login screen, original logo
(2,172px source width), all-50-state copy and preserved navy/white layout. At its
1,363px viewport, document width was 1,348px with no horizontal overflow. Its log
contained browser-extension metadata errors; no application error appeared in the
returned entries. The authenticated UI journeys passed in CI; a full authenticated
UI journey on the deployed service was **not run**. Actual live signed-in behavior
was verified through HTTPS APIs as listed above.

Render's warning/error log query for **17:19:28–17:21:30 UTC** succeeded with zero
matching entries. This bounded observation is not a claim of error-free future
operation. The image build retained its harmless existing system-UID warning.
Backup restoration remains untested.

### Remaining coverage and product work

All 50 states are searchable through federal programs and have official agency
directory links. Current listings are present in 19 states, and county coverage
remains partial. Nationwide pre-foreclosure notices, additional county tax-deed /
tax-lien feeds, HUD/GSA imports, and the remaining state DNR inventories need
approved sources and additional adapters. No paid subscription or redistribution
license was acquired. Source cancellations and same-day closing times still require
confirmation at the official listing. See [SOURCES.md](SOURCES.md).

The earlier limits for email ownership verification, automatic password recovery,
backup restoration, comparables, independent valuations and deal-model assumptions
continue to apply. The original screenshot files above show the initial Texas
release; they are not presented as screenshots of the expanded signed-in UI.

## Free public API integration — September 14, 2026

Added authenticated reference research through Census geography, FEMA NFHL, USGS elevation, USDA NRCS soils and NC OneMap parcels. These are separate from sale inventory and model inputs; MLS remains unconnected. See [FREE_DATA.md](FREE_DATA.md). No dependencies, schema, account records, infrastructure plans or payment configuration changed.

### Local gates

Commands ran from `beta/` unless marked repository root. Exit statuses below are observed; unavailable browsers and upstream responses are not called passes.

| Command | Result | Evidence / limit |
| --- | --- | --- |
| `.venv/bin/ruff format --check landwolf tests scripts` | **Passed** (exit 0) | Command completed successfully. |
| `npm run format:check` | **Passed** (exit 0) | Command completed successfully. |
| `.venv/bin/ruff check landwolf tests scripts` | **Passed** (exit 0) | Command completed successfully. |
| `npm run lint` | **Passed** (exit 0) | Command completed successfully. |
| `.venv/bin/mypy landwolf` | **Passed** (exit 0) | Command completed successfully. |
| `npm run typecheck` | **Passed** (exit 0) | Command completed successfully. |
| `.venv/bin/pytest -q -m 'not browser'` | **Passed** (exit 0) | 165 passed; 3 browser tests deselected for this unit/API command. |
| `npm run build` | **Passed** (exit 0) | Command completed successfully. |
| `.venv/bin/pytest -q -m browser` | **Failed** (exit 1) | 3 failed before UI execution: default Playwright Chromium executable missing. |
| `.venv/bin/python -m build` | **Passed** (exit 0) | Command completed successfully. |
| `.venv/bin/python scripts/check_package.py` | **Passed** (exit 0) | Command completed successfully. |
| `.venv/bin/bandit -r landwolf` | **Passed** (exit 0) | Command completed successfully. |
| `.venv/bin/pip-audit --local --skip-editable` | **Passed** (exit 0) | No known dependency vulnerabilities; editable application excluded from advisory lookup, covered by source tests/scanner. |
| `npm audit --audit-level=moderate` | **Passed** (exit 0) | Zero dependency vulnerabilities. |
| `npm run secrets` | **Passed** (exit 0) | No configured secret findings. |
| `git diff --check` | **Passed** (exit 0) | Repository root: no whitespace errors. |
| `git status --short` | **Passed** (exit 0) | Repository root: only intended beta files modified or added. |
| `PYTHONPATH=. /workspace/scratch/bae2278276c6/legacy-venv/bin/pytest -q` | **Failed** (exit 1) | Repository root: 48 passed, 5 existing failures from missing legacy environment-example fixtures; legacy code unchanged. |
| `.venv/bin/python -m landwolf.cli check-research` | **Passed** (exit 0) | Live Dallas point: Census, FEMA, USGS and soils ready; NC correctly outside coverage. |
| `.venv/bin/python -m landwolf.cli check-research --latitude 35.7804 --longitude -78.6391` | **Failed** (exit 1) | Live Raleigh aggregate: four sources ready; NC unavailable. Earlier full Raleigh check passed; later single-source diagnostic returned one parcel in one attempt. Neither erases this failed run. |
| `.venv/bin/python -m landwolf.cli sync` | **Passed** (exit 0) | All seven automated listing sources ready. Raw snapshot counts: AR 2,288; TX 30; USDA 18; Treasury 15; IRS 10; AK 171; MI 8. Directory entries excluded; raw snapshot counts differ from date-filtered current search. |

The final responsive-header adjustment was followed by another successful run of both format checks, both lint commands, Python/TypeScript type checks, the 165-test unit/API suite and `npm run build`. Production package build/validation and all four security commands also ran again successfully after that adjustment.

`PLAYWRIGHT_CHROMIUM_EXECUTABLE=/workspace/scratch/bae2278276c6/browser-tools/chromium .venv/bin/pytest -q -m browser` also **Failed** (exit 1): all three journeys stopped because the alternate local Chromium crashed with SIGSEGV at launch. This is not browser verification.

`.venv/bin/python scripts/check_postgres.py` was **Not run locally** because a disposable PostgreSQL service is unavailable here. Hosted CI must supply PostgreSQL 18 and normal Chromium before deployment.

New tests exercise authenticated/CSRF-protected research, rate/capacity limits, source coordinate identity, bounded requests/responses, redirect/endpoint rejection, missing data, malformed schemas, independent source failures, numeric sentinels, multiple parcel candidates, cache expiry and absence of database changes. The new browser journey uses real browser → API → parsers → isolated database, replacing only upstream HTTP transport with explicit synthetic fixtures. It covers approximate-location labels, missing values, source links, tablet/mobile widths, no model prefilling, input-edit races and sign-out cleanup.

Initial intermediate Ruff line-length and mypy optional-value errors were corrected before these gates; no suppression or gate relaxation was added. Existing FastAPI/Starlette deprecation warnings and npm environment-config warnings remain.

### Hosted check and source recovery before deployment

Initial application commit `3bc8154922e5b85d14e49e3ba3c808eae38d54a1`, tree
`4ce45f10f6ddcb03a031377bc2de21bcc1841ccd`, was published only to the beta branch.
Push run [34880072884](https://github.com/lupu-spec/Landwolf/actions/runs/34880072884)
and PR run [34880076670](https://github.com/lupu-spec/Landwolf/actions/runs/34880076670)
passed install, format, lint, types, all 165 unit/API tests and PostgreSQL 18.
The new public-research Chromium journey and original complete journey passed;
the nationwide journey failed because its global `.source-card` selector counted
five newly added reference-source cards alongside the one filtered sale feed.
The test now scopes the existing count/name assertions to `#source-cards` and
additionally asserts that all five reference cards remain present. No behavior
assertion, gate or test was removed. Package/security steps in these two runs were
skipped after the browser failure, not passed. No deployment was triggered.

The second aggregate Raleigh command also exited 1 at **18:17:36 UTC**, with NC
unavailable and the other four sources ready. The intervening isolated NC request
had returned one candidate parcel in one attempt. This intermittent source result
remains documented; the beta displays unavailable findings independently and does
not assign a zero value or infer low risk from them.

### Final hosted gates and observed deployment

Verified/deployed commit: `5686a2b1a3e410f40df39f782fd6eefd88c825c2`.
Tree: `7d3deb5c86aa4f9926b3479726255f8a2fae3dfb`. The application code is identical
to `3bc8154`; the follow-up corrected the scoped browser assertion and recorded
evidence. The original logo and navy/white appearance remain in place.

Both [push run 34880426547](https://github.com/lupu-spec/Landwolf/actions/runs/34880426547)
(job `104098072305`) and
[PR run 34880429321](https://github.com/lupu-spec/Landwolf/actions/runs/34880429321)
(job `104098081768`) completed **successfully**. Observed job logs confirm:

| Hosted command / gate | Observed result |
| --- | --- |
| `uv sync --frozen --dev`, `npm ci`, `.venv/bin/playwright install --with-deps chromium` | **Passed** |
| `.venv/bin/ruff format --check landwolf tests scripts`, `npm run format:check` | **Passed** |
| `.venv/bin/ruff check landwolf tests scripts`, `npm run lint` | **Passed** |
| `.venv/bin/mypy landwolf`, `npm run typecheck` | **Passed** |
| `.venv/bin/pytest -q -m 'not browser'` | **Passed** — 165 tests; browser cases run separately |
| `.venv/bin/python scripts/check_postgres.py` | **Passed** — disposable PostgreSQL 18, authentication, nationwide filters, nulls, dates, pagination and saves |
| `npm run build`, `.venv/bin/pytest -q -m browser` | **Passed** — all 3 Chromium journeys, including public research and the corrected nationwide coverage check |
| `.venv/bin/python -m build`, `.venv/bin/python scripts/check_package.py` | **Passed** — source archive and deployable wheel |
| `.venv/bin/bandit -r landwolf` | **Passed** — no findings |
| `.venv/bin/pip-audit --local --skip-editable`, `npm audit --audit-level=moderate` | **Passed** — no known dependency vulnerabilities |
| `npm run secrets` | **Passed** — no configured secret findings |
| `git diff --check`, `git status --short` | **Passed** |

All commands exited 0. Existing legacy `Test`, release/preflight workflows remain
separate failures; they were not bypassed or represented as beta successes. The
local legacy suite's 48 passes / 5 missing-fixture failures are recorded above.
No merge into `main` or deployment of legacy production occurred.

After these gates, Render service `srv-dak1lvh42hec73blur00` was confirmed to use
the beta branch with auto-deploy off. Manual deploy `dep-dak3o3p5efls73fup88g`
selected the verified commit, completed its build/pre-deploy rollout, and reached
**live at 18:25:58 UTC** on September 14. The existing service and PostgreSQL
database were reused; no new infrastructure, plan change or API subscription was
created. [Deployed beta](https://landwolf-free-beta.onrender.com/).

The explicit command
`.venv/bin/python /workspace/scratch/bae2278276c6/check_free_research_deployed.py`
**Passed** (exit 0), running against real HTTPS and the deployed database from
**18:26:39–18:26:58 UTC**. It verified:

- Observed health and disabled payments; deployed JavaScript, CSS and logo bytes
  matched the exact local production build by SHA-256.
- Anonymous research returned 401, missing CSRF returned 403, invalid coordinates
  returned 422, and authenticated research succeeded. Cookies were Secure,
  HttpOnly and SameSite=Strict.
- The source API retained all 50 states, seven sale-feed adapters and five research
  sources. Current listing search and coverage counts agreed on 2,529 records.
- Dallas City Hall's street address returned **ready** Census, FEMA, USGS and NRCS
  results, correctly labeled as an approximate Census location. NC parcels were
  correctly outside that source's coverage.
- The NC State Capitol point returned **ready** results from **all five sources**.
  NC parcel `1703790137` was returned with its value type explicitly `Assessed`;
  source text states that tax values are not market values or asking prices.
- A repeated NC query returned cached public facts with unchanged original
  retrieval timestamps. Public owner fields were absent from the returned facts.
- A synthetic account's saved record persisted through research and logout/login;
  the revoked session could not research. The test save was removed and the final
  test session revoked. One synthetic account was created, without sending email;
  its generated credentials were never printed or persisted.

These are observed sample locations, not proof of complete nationwide records or
continuous provider availability. In particular, the earlier local NC interruptions
remain relevant; the deployed successful check does not erase them.

A controlled cloud browser reloaded the deployed login page, observed the supplied
brand, free-beta/all-50-state copy and sign-in gate, and measured a 1,348px document
inside a 1,363px viewport with no horizontal overflow. An initial image-role locator
timed out; no image-dimension result is claimed from that failed call. A subsequent
DOM/layout check succeeded, and the HTTPS check independently verified exact logo
bytes. An authenticated browser journey on the live Render service was **Not run**;
authenticated Chromium flows ran in hosted CI, while actual deployed authentication
and public APIs were exercised through HTTPS above.

Render application warning/error query **18:25:19–18:28:12 UTC** returned zero
matching entries. This is a bounded observation, not a guarantee of future uptime.

Changed files: `landwolf/research.py` implements the bounded public adapters and
contracts; `main.py` adds authenticated research and source discovery; `cli.py`
adds explicit live research checks; `web/app.ts`, `web/index.html`, `web/styles.css`
add the research workflow; research fixtures/tests and the browser suite cover its
behavior. `AGENTS.md`, `README.md`, `SOURCES.md` and `FREE_DATA.md` document commands,
coverage and limitations. No database migration or new dependency was required.

The final follow-up to this log changes documentation only; it does not change the
deployed runtime. MLS, nationwide assessor/deed/title/lien records, independent
market valuations, email verification/password recovery and tested backup restore
remain outside the completed feature scope.


## Production domain promotion — September 14, 2026

Owner authorized production at `landwolf.ai` / `www.landwolf.ai`, with payments
still disabled. This change reuses the rebuilt service and database, preserves
accounts/saves and branding, and adds an explicit three-origin allowlist. Writes
require both an allowed Origin and its matching Host; cookies remain host-only.
Render performs the canonical apex/www redirect. No dependencies or schema changed.

Local commands ran from 20:47 UTC after the final runtime/test edits:

| Command (from beta unless noted) | Observed local result |
| --- | --- |
| `.venv/bin/ruff format --check landwolf tests scripts` | **Passed** (exit 0) |
| `npm run format:check` | **Passed** (exit 0) |
| `.venv/bin/ruff check landwolf tests scripts` | **Passed** (exit 0) |
| `npm run lint` | **Passed** (exit 0) |
| `.venv/bin/mypy landwolf` | **Passed** (exit 0) |
| `npm run typecheck` | **Passed** (exit 0) |
| `.venv/bin/pytest -q -m 'not browser'` | **Passed** (exit 0) — 210 tests |
| `.venv/bin/python scripts/check_postgres.py` | **Failed** (exit 1) — disposable PostgreSQL unavailable locally |
| `npm run build` | **Passed** (exit 0) |
| `.venv/bin/pytest -q -m browser` | **Failed** (exit 1) — Chromium executable unavailable; no browser pass claimed |
| `.venv/bin/python -m build` | **Passed** (exit 0) |
| `.venv/bin/python scripts/check_package.py` | **Passed** (exit 0) |
| `.venv/bin/bandit -r landwolf` | **Passed** (exit 0) |
| `.venv/bin/pip-audit --local --skip-editable` | **Passed** (exit 0) |
| `npm audit --audit-level=moderate` | **Passed** (exit 0) |
| `npm run secrets` | **Passed** (exit 0) |
| `git diff --check` | **Passed** (exit 0) |
| `git status --short` | **Passed** (exit 0) |
| `PYTHONPATH=. /workspace/scratch/bae2278276c6/legacy-venv/bin/pytest -q` | **Failed** (exit 1) — 48 passed, 5 existing missing-env-fixture failures |
| `.venv/bin/python -m landwolf.cli sync` | **Passed** (exit 0) |

The initial targeted command `.venv/bin/pytest -q tests/test_domains.py
tests/test_config.py` exited 1 (69 passed / 1 failed): the new save-persistence
assertion used `items` instead of the existing response key `results`. The assertion
was corrected, then the complete 210-test suite passed without weakened gates.
`.venv/bin/ruff format landwolf tests scripts` and `npm run format` both exited 0;
the resulting diff was reviewed. Existing httpx/Starlette and npm environment
deprecation warnings remain. Production build, package and all security scanners
passed; live source sync passed independently of fixture tests.

Hosted CI, production deployment and final DNS/HTTPS checks are pending at this
checkpoint; this section does not claim them as passed. The Render CLI is not
installed locally, so CLI Blueprint validation has not run.

DNS inspection found Spaceship authoritative servers `launch1.spaceship.net` and
`launch2.spaceship.net`; apex A is already `216.24.57.1`, and www CNAME still targets
`landwolf-mw8m.onrender.com`, both with 60-second TTL. Existing domains were verified
and certificated on the legacy service, redirecting apex to www. Desired cutover
uses the rebuilt service, reverses that redirect, and updates only the www CNAME
to `landwolf-free-beta.onrender.com`. Apex has no AAAA or CAA records.

Spaceship's browser stayed on an explicit Cloudflare security-verification loop
after one reload; botDetection reported `challenge_loop` and attempts stopped.
No registrar DNS mutation has occurred at this checkpoint.


### Production deployment and domain association — observed result

Runtime commit `9483d455fa0389960b3dc3fa7161618781ab431e`, tree
`00ed55464fb8fef870d6dca6e2b39388a0680c8d`, passed both hosted workflows:
[push 34895361976](https://github.com/lupu-spec/Landwolf/actions/runs/34895361976)
(job `104147881035`) and
[PR 34895367562](https://github.com/lupu-spec/Landwolf/actions/runs/34895367562)
(job `104147898978`). All configured steps succeeded. Observed push-job logs confirm
210 unit/API tests, all three Chromium journeys, disposable PostgreSQL integration,
format/lint/type checks, production build/package, Bandit, both dependency audits,
secret scanning and diff integrity. Each hosted command listed in the local table
above (except the separately run legacy suite and live source sync) exited 0; hosted
setup also ran `uv sync --frozen --dev`, `npm ci` and
`.venv/bin/playwright install --with-deps chromium` successfully. The existing legacy
Test/release/preflight failures are separate and were not bypassed or called passed.

An initial Git fetch briefly returned the old branch tip, so the staged-tree
comparison failed. A subsequent explicit ref fetch obtained the published commit;
`git diff --cached --quiet 9483d455fa0389960b3dc3fa7161618781ab431e` exited 0. The
local branch was then aligned without discarding changes. GitHub's created tree
exactly matched local `git write-tree`.

Render merged only `LANDWOLF_PUBLIC_ORIGIN`, `LANDWOLF_ADDITIONAL_ORIGINS` and
`LANDWOLF_PAYMENTS_ENABLED`, preserving other environment variables and the database.
The environment update itself triggered deploy `dep-dak5tkvf3r2c73c76r9g`; no duplicate
manual trigger was issued. Render confirmed the exact runtime commit above and
**live at 20:54:15 UTC**, September 14, 2026. Automatic branch deployment remains off.
Service `srv-dak1lvh42hec73blur00` and its existing PostgreSQL database were reused;
no new service, plan upgrade, billing integration or database migration was created.

**Passed**, exit 0:
`LANDWOLF_CHECK_ORIGIN=https://landwolf-free-beta.onrender.com .venv/bin/python
/workspace/scratch/bae2278276c6/check_production_deployed.py`, from beta,
20:54:36–20:54:53 UTC. Actual deployed HTTPS verified health, disabled payments,
exact built JS/CSS/original-logo bytes, FREE ACCESS text, anonymous denial, secure
host-only cookies, authenticated search/research, CSRF, coordinate validation,
50-state coverage metadata, seven sale feeds, five research sources and 2,529
current listings. Dallas address research returned four ready national sources;
Raleigh returned all five sources ready. Source-cache timestamps and saved-property
persistence across logout/login passed. That check removed its own test save and
revoked its session; its synthetic account remains, with no email sent or credentials
printed/persisted. This remains sample availability, not complete nationwide coverage.

The legacy primary `www.landwolf.ai` binding was removed in Render; Render also
removed its associated apex redirect. The legacy service and database were retained.
Adding `landwolf.ai` to the rebuilt service automatically added a www-to-apex
redirect. The apex verified immediately; www initially showed Waiting for DNS.
After the explicit Verify action, the Render dashboard showed **Verified** and
**Certificate Issued** for **both domains**. The www row explicitly redirects to
`landwolf.ai`. The existing Render subdomain remains enabled.

This is observed Render configuration, **not a successful custom-domain HTTP check**:

- The Python HTTPX batch requested `https://landwolf.ai/`, `/api/health`, and
  `https://www.landwolf.ai/`; all returned ReadTimeout. The diagnostic batch exited
  0 because it records failures, so its exit does not indicate successful requests.
- HTTP requests to both names returned a workspace-generated Site Unavailable page
  with `x-openai-site-blocked: true`, not an application response or verified HTTPS
  redirect. The cloud browser's apex visit showed 502 / connection refused. No
  routing fix or nationwide availability is inferred from these failed checks.
- `.venv/bin/python /workspace/scratch/bae2278276c6/check_domain_account_continuity.py`
  created one synthetic account and save on the Render address, then paused before
  visiting the apex. It was interrupted after the access block was identified
  (exit 1); no completed evidence/cleanup file was written. Live cross-domain
  continuity is **Not run**, and cleanup of that single synthetic save/session was
  **not confirmed**. Account/save continuity passed in the isolated tests.
- The full apex variant of `check_production_deployed.py` was **Not run** after the
  access block. No authenticated custom-domain browser journey is claimed.

**Passed**, exit 0, both commands from beta:
`.venv/bin/python /workspace/scratch/bae2278276c6/check_production_dns.py before`
and the same command with `after`. Google and Cloudflare public resolvers agreed
at 20:52 and 20:59 UTC: apex A `216.24.57.1` and www CNAME
`landwolf-mw8m.onrender.com`, TTL 60; Spaceship remains authoritative. Neither
resolver returned apex MX/TXT/AAAA/CAA records; www's alias chain has no AAAA address.
No DNS records were changed. These observations verify public resolution at those
resolvers, not every cache on the internet. The remaining registrar change is:

| Host | Type | Required target | TTL |
| --- | --- | --- | --- |
| `www` | CNAME | `landwolf-free-beta.onrender.com` | 60 seconds (or provider default) |

Keep the existing apex A record. Leave unrelated records intact. Render accepted
the existing www alias, which already resolves into Render, but it still
names the old service; update it to match the new service before retiring legacy.
Spaceship remained blocked by its security-verification loop; the control-browser
skill required stopping there after one recovery attempt. The owner must make
the registrar edit or complete secure browser access. Then verify both custom
domains from an unrestricted browser, including www/HTTP redirects and sign-in.
The deployment is complete; final DNS cleanup and custom-domain verification remain
open. No claim is made that every DNS server updated or every user can reach it.

A subsequent browser visit to the Render address observed the original logo,
FREE ACCESS, all-50-state description and sign-in gate. No authenticated cloud
browser journey was run. A bounded Render application warning/error query for
20:53:39–21:00:00 UTC returned zero matching entries.

A local Python/YAML check parsed `render.beta.yaml`, instantiated Settings from its
non-secret environment values, and confirmed disabled payments, both domain names,
auto-deploy off and preserved resource names (exit 0). This is application
configuration validation; Render CLI/platform Blueprint validation remains Not run.

This follow-up records evidence only. The deployed runtime is unchanged. Email
verification/password recovery, a tested backup restoration, MLS access and complete
county-level foreclosure/tax/parcel coverage remain outside this release.

## Responsive heading spacing — September 19, 2026

The login-page headings now use responsive line spans instead of hidden decorative
break elements, retaining natural word spacing at small widths. A Chromium regression
assertion checks the rendered 790px
text for “Understand the opportunity.” and “Your next opportunity starts here.”

After the final code change, these commands passed locally: `uv sync --frozen --dev`;
both configured format checks; both linters; Python and TypeScript type checks;
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
