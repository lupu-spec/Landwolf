# LandWolf beta verification

Observed locally on September 14, 2026, on branch `codex/landwolf-beta-rebuild`,
based on `5307de0a11fd75a7c51bdf5243f3e13179b95d38`. Results describe the new
`beta/` application, not a deployed service or the legacy billing application.
Python 3.12 and Node 24 were used with the committed dependency locks.

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
| Production PostgreSQL integration | **Not run** | No separate beta database has been provisioned; local API/browser tests use SQLite. |
| Deployed HTTPS health, session, browser, and live refresh checks | **Not run** | Sign-in and billing are ready. A temporary-origin deployment was rejected by automatic approval review. The revised configuration uses Render's assigned HTTPS URL and awaits its hosted browser gate before deployment. |
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
| Render beta provisioning and deployed verification | **Not run** | No new beta service/database has been created. Billing is ready, and the approved beta branch/path resolves to the two intended resources. The safer origin configuration is undergoing verification before resubmission. |

The existing Render app and database were inspected without modification. The
beta's Docker build, production PostgreSQL integration, and deployed HTTPS/browser
checks remain outstanding. Hosted CI success is not evidence of deployment.

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

Hosted browser verification for this revision and the actual Docker/PostgreSQL/HTTPS
deployment checks remain outstanding. Earlier CI results above belong to the earlier
source commit; they are not claimed as verification of this correction.

## Remaining product and deployment limits

Live coverage is Texas GLO public-sale inventory only. Other states, county tax
sales, foreclosure feeds, municipal surplus, ownership, liens, flood overlays,
comparables, and independent valuations are not connected. The UI reports these
gaps and source freshness. Published location points are not surveyed boundaries.
Scenario outputs depend on user assumptions and omit correlated market shocks;
see [MODEL.md](MODEL.md). Asking prices never establish resale value.

Email ownership verification and automatic password recovery remain to be added
before broad public enrollment. Deployment requires a new PostgreSQL database,
an explicit HTTPS origin, reviewed backup/retention settings, and the deployment
checks above. Initial operation uses one worker/instance. The Render configuration
may incur hosting charges and has not created or modified any hosted resource.

Review screenshots: [login](preview-login.png), [property search](preview-explore.png),
[scenario analysis](preview-analysis.png), [mobile](preview-mobile.png).
