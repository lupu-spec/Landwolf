# v0.5.0 — research decisions

**Live in staging and production.** [PR #20](https://github.com/lupu-spec/Landwolf/pull/20)
merged as `c333667f6a66b5dae870738387d01755f9ba485c`. The exact staging-tested
commit is running on production. Candidate `c63c210064338d98ef83ecd77f540aa68f9eefd9`
passed all required CI before promotion.
The user explicitly approved publication to the public repository on October 5,
resolving the earlier automatic approval rejection. The local Git client lacked
credentials, so the connected GitHub app published the source instead. Uploaded
Git tree hashes were verified against the local candidate before moving the branch.
Observed deployment and independent live-verification evidence appears below.

## Scope

Private research in property details and Hunts: intended-use goals and requirements,
prioritized verification questions, remaining-cost allowances, cost/delay stress
tests, two-property reversal thresholds, shared planning-authority questions,
recorded evidence, pause reasons, on-open reconsideration and browser print packets.
All 50 states use the same workflow. No new provider, paid model, worker, messaging
service, dependency, or infrastructure resource is introduced. Existing Stripe,
pilot access, persistent sessions, source adapters and owner-only coverage remain.

Acquisition/quotes/proceeds are user assumptions or explicitly labeled source prices;
the tool does not create a valuation, prove access or clear a parcel from a point.
Requirements cannot be offset by favorable economics. Missing costs remain unknown.
General rules are limited to permitted-use evidence with explicit property
applicability. Shared question briefs never automatically transfer answers.

## Storage and operations

Schema 9 additively creates `lw2_research_cases` and `lw2_research_goals`.
Existing accounts, sessions, listings, billing, feedback and Hunts are preserved.
Research is scoped by immutable account ID plus listing ID; linked Hunts are checked
against that account. All new routes require authentication and billing access;
writes also use the existing origin, JSON and CSRF checks. PostgreSQL account locks
and optimistic revisions serialize writes. Conflicting edits return 409. Database
failures roll back and return 503 without discarding the browser's edits.

Each account is capped at 50 research records, each with seven bounded evidence
topics and 20 material change events. State recomputes from existing local inventory
and recorded answers on opening. Provider timestamps alone do not create events.
The source facts needed for research survive inventory removal as a private snapshot;
the property is then marked unavailable and cannot satisfy a reconsideration trigger.
Deleting a Hunt removes its linked research, as stated in the confirmation.

The migration is transactional and idempotent on SQLite/PostgreSQL. Version 8
images reject schema 9; prefer a tested fix forward. An old-image rollback requires
a coordinated database restore, including reconciliation of post-backup writes.
The existing paid production PostgreSQL service is retained. Backup availability
was checked before promotion; CI rehearsed dump/restore on a disposable database
with populated research rows.

## Verification commands and current results

Run from `beta/` unless marked root. Results were observed locally and in the
[passing final CI run](https://github.com/lupu-spec/Landwolf/actions/runs/37278173446)
on 2026-10-05. Successful commands exited 0. Local environment failures are retained
separately and are not represented as passes.

| Command | Current result |
| --- | --- |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed; 62 Python files and frontend formatting |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | Passed; 28 Python modules and TypeScript |
| `npm run test:unit`; `.venv/bin/pytest -q -m 'not browser'` | Passed; 9 frontend and 395 backend tests; 36 browser tests deliberately deselected for the backend command |
| `.venv/bin/python scripts/check_postgres.py`; `.venv/bin/python scripts/check_restore.py` | Passed hosted; PostgreSQL research/authentication/persistence checks and exact restore digests across 23 tables. Not run locally: disposable PostgreSQL unavailable |
| `npm run build` | Passed; browser production bundle generated |
| `.venv/bin/pytest -q tests/test_decision_browser.py -x` | Failed at browser launch; Chromium executable absent following failed browser download |
| `.venv/bin/pytest -q -m browser` | Passed hosted; all 36 Chromium/WebKit browser tests, including four new complete research journeys at 390px and 1440px |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed; runtime/branding assets and frontend tests included |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable`; `npm audit --audit-level=moderate`; `npm run secrets` | Passed; no static security findings or known dependency vulnerabilities; editable application excluded from dependency audit as configured |
| `uv lock --check`; `npm ci` | Passed; metadata consistent and 191 locked npm packages installed; dependency versions unchanged |
| `PYTHONPATH=. .venv-legacy/bin/pytest -q` (root) | Passed; 53 tests |
| `LANDWOLF_DATABASE_URL=sqlite:////tmp/landwolf-research-release/sources.db .venv/bin/python -m landwolf.cli sync` | Passed; all eight implemented listing adapters ready; this is an isolated verification database, not proof of production source state |
| `git diff --check`; `git status --short` (root) | Passed before documentation updates; clean committed runtime candidate |
| `.venv/bin/python scripts/check_hosted_staging.py --environment staging` with `GITHUB_SHA=c333667f6a66b5dae870738387d01755f9ba485c` | Passed hosted; exact identity/HTTPS/health, research, four customer journeys, session restart/cache/logout and coverage restrictions |
| `.venv/bin/python scripts/check_hosted_staging.py --environment production` with the same `GITHUB_SHA` | Passed hosted; exact identity/HTTPS/health, live billing enabled, four paywall/customer journeys, session restart/cache/logout and coverage restrictions |

Initial focused research run passed 20 backend tests. Initial lint/type findings
were corrected. A full-suite run exposed FastAPI's lazy included-router object in
an existing security inspection; registration now uses ordinary app routes without
weakening the security test. A local Playwright installation attempt failed because
the download returned invalid/truncated archives. Hosted Chromium/WebKit CI later
completed successfully. These earlier failures are not recorded as passing gates.

Final API coverage includes account isolation, billing denial, origin/CSRF checks,
optimistic revision conflicts, storage failure rollback, bounded case/history counts,
evidence validation, cost invariants, schema-8 migration and retained property data.
The separate 22-test research subset passed before the complete 395-test run.
The final root legacy suite passed 53 tests. Existing framework deprecation and npm
proxy-environment warnings were retained; dependencies were not upgraded.

The first hosted run, [37276811182](https://github.com/lupu-spec/Landwolf/actions/runs/37276811182),
passed backend/PostgreSQL/restore and 32 existing browser tests, but four new
journeys failed because nested select options contaminated implicit labels. Explicit
accessible labels corrected the product defect. The next run,
[37277614518](https://github.com/lupu-spec/Landwolf/actions/runs/37277614518),
passed through save/retry, allowance/return calculations, comparisons and shared
briefs, then failed in the test harness: Playwright invoked the function returned
by an assignment while installing the print hook. A wrapping setup function fixes
that harness error without changing or removing any print-content assertions.
Neither failed run is counted as a complete passing release gate.

Production backup availability was checked before promotion: the connected Render
API reports an available paid `basic_256mb` PostgreSQL 18 instance, and its logs show
successful backup-marker archival at 07:04:03 UTC and WAL archive completion at
07:14:02 UTC on October 5. [Render's recovery documentation](https://render.com/docs/postgresql-backups)
provides continuous PITR for paid databases. The precise current recovery-window
endpoint was not exposed. Direct read-only SQL was blocked by the existing empty
external IP allowlist; that network restriction was preserved. The disposable CI
database restore is separate from these production archive observations.

Fresh isolated source counts were AK DNR 170, Arkansas COSL 0, IRS 1, Michigan DNR
28, MnDOT 4, Texas GLO 31, Treasury 19 and USDA 19. Directory-only sources remain
directory-only. No new upstream integration or coverage claim is made.

## Observed deployments and verification limits

| Environment | Version / immutable runtime commit | Render deployment | Live UTC, 2026-10-05 | Independent verification |
| --- | --- | --- | --- | --- |
| Staging | v0.5.0 / `c333667f6a66b5dae870738387d01755f9ba485c` | `dep-db1l7sbncjis73f9qhpg` | 07:39:25 | [Hosted checks 37278867596](https://github.com/lupu-spec/Landwolf/actions/runs/37278867596), completed before production promotion |
| Production | v0.5.0 / `c333667f6a66b5dae870738387d01755f9ba485c` | `dep-db1l9hh42hec73d7mj5g` | 07:42:50 | [Hosted checks 37278849695](https://github.com/lupu-spec/Landwolf/actions/runs/37278849695), all assertions passed at 07:43:43 |

The final candidate passed [legacy tests](https://github.com/lupu-spec/Landwolf/actions/runs/37278173470)
and [release preflight](https://github.com/lupu-spec/Landwolf/actions/runs/37278173463)
in addition to the full beta gate. This totals 395 backend, 9 frontend, 36 browser
and 53 legacy tests. Staging and production each passed four additional live browser
journeys and Chromium/WebKit restart/cache/logout checks.

Render logs observed schema 9 migration and successful application startup. No
production warning/error logs were returned from deployment start through 07:43:55
UTC. Existing Render service/database IDs, billing configuration and external
database access restrictions were retained. No paid resources or dependencies were
added. Existing hosting and storage capacity still have finite limits.

Direct workspace HTTPS probes passed for staging. The direct production probe
failed JSON decoding because its response was not JSON; the independent hosted
production checks passed exact version/commit, HTTPS, health and billing mode.
CI browser screenshots were archived, but local artifact retrieval returned HTTP
403, so no manual screenshot review is claimed. Automated overflow assertions and
print-content checks passed; physical printer and device testing was not performed.

Live production checks use a disposable unpaid account and prove the paywall,
authentication and coverage boundary without making a charge or impersonating an
owner/subscriber. Entitled research flows are exercised against live staging and
isolated CI. One disposable non-cohort verification account remains per environment.
Production source-state rows were not independently queried; isolated source-sync
results do not establish complete nationwide coverage or every production feed state.

## User entry points

- Property details → **Decision research** / **Research your decision**.
- Select a Hunt to inherit its research goal, or keep a property-specific goal.
- **Calculate preview** tests edits without persistence; **Record research** retains
  answers, inputs and history. **Print displayed research** exports the displayed case.
- Hunt → **Research this Hunt**: edit shared goal, reopen cases, compare two properties,
  inspect reconsideration, and copy/print shared questions. Copying sends no messages.

Nationwide parcel geometry and continuous external report reruns remain outside this
release, as deferred in the approved roadmap. No new infrastructure capacity is
claimed or purchased. Manual evidence is attributed to the customer, never presented
as independent LandWolf certification.
