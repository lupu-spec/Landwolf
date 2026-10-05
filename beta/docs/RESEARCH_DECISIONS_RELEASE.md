# v0.5.0 — research decisions

**Candidate only — not deployed.** Runtime candidate `1b640a5` is committed on
`codex/research-decisions`. Production remains at the observed v0.4.4 release.
Automatic approval review rejected the GitHub push twice, including after the
connected GitHub account and Render service confirmed the existing public,
account-owned `lupu-spec/Landwolf` destination. Explicit publication approval is
required to continue. No alternate publication path was attempted. Hosted CI,
staging and production deployment have not run for this candidate.

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
The existing paid production PostgreSQL service is retained. Verify platform backup
availability before production promotion; CI rehearses dump/restore on a disposable
database with populated research rows.

## Verification commands and current results

Run from `beta/` unless marked root. Results below were observed locally on
2026-10-05 against the final runtime candidate. Successful commands exited 0;
the targeted browser command exited 1. Hosted evidence will be appended only
after observation; a branch or candidate is not a deployed release.

| Command | Current result |
| --- | --- |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed; 62 Python files and frontend formatting |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | Passed; 28 Python modules and TypeScript |
| `npm run test:unit`; `.venv/bin/pytest -q -m 'not browser'` | Passed; 9 frontend and 395 backend tests; 36 browser tests deliberately deselected for the backend command |
| `.venv/bin/python scripts/check_postgres.py`; `.venv/bin/python scripts/check_restore.py` | Not run; disposable PostgreSQL is unavailable locally; hosted gates blocked by publication |
| `npm run build` | Passed; browser production bundle generated |
| `.venv/bin/pytest -q tests/test_decision_browser.py -x` | Failed at browser launch; Chromium executable absent following failed browser download |
| `.venv/bin/pytest -q -m browser` | Not run to completion; all 36 browser tests remain an outstanding hosted gate |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed; runtime/branding assets and frontend tests included |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable`; `npm audit --audit-level=moderate`; `npm run secrets` | Passed; no static security findings or known dependency vulnerabilities; editable application excluded from dependency audit as configured |
| `uv lock --check`; `npm ci` | Passed; metadata consistent and 191 locked npm packages installed; dependency versions unchanged |
| `PYTHONPATH=. .venv-legacy/bin/pytest -q` (root) | Passed; 53 tests |
| `LANDWOLF_DATABASE_URL=sqlite:////tmp/landwolf-research-release/sources.db .venv/bin/python -m landwolf.cli sync` | Passed; all eight implemented listing adapters ready; this is an isolated verification database, not proof of production source state |
| `git diff --check`; `git status --short` (root) | Passed before documentation updates; clean committed runtime candidate |

Initial focused research run passed 20 backend tests. Initial lint/type findings
were corrected. A full-suite run exposed FastAPI's lazy included-router object in
an existing security inspection; registration now uses ordinary app routes without
weakening the security test. A local Playwright installation attempt failed because
the download returned invalid/truncated archives. Hosted Chromium/WebKit CI must
complete before release. These failures are not recorded as passing gates.

Final API coverage includes account isolation, billing denial, origin/CSRF checks,
optimistic revision conflicts, storage failure rollback, bounded case/history counts,
evidence validation, cost invariants, schema-8 migration and retained property data.
The separate 22-test research subset passed before the complete 395-test run.
The final root legacy suite passed 53 tests. Existing framework deprecation and npm
proxy-environment warnings were retained; dependencies were not upgraded.

Fresh isolated source counts were AK DNR 170, Arkansas COSL 0, IRS 1, Michigan DNR
28, MnDOT 4, Texas GLO 31, Treasury 19 and USDA 19. Directory-only sources remain
directory-only. No new upstream integration or coverage claim is made.

## Remaining release gates

1. Obtain explicit approval for publishing the source to the existing public
   GitHub repository, then push the candidate and open its production-base PR.
2. Complete required CI, including all Chromium/WebKit journeys, PostgreSQL and
   backup/restore checks; resolve any findings without weakening gates.
3. Reconcile the staging branch with the production baseline and test the exact
   promotion commit on the existing isolated staging service/database.
4. Verify production backup availability before schema migration. The connected
   Render service reports an available paid PostgreSQL instance, but no current
   recovery point was independently observed during this candidate preparation.
5. Deploy to the existing production service; observe exact version/commit,
   HTTPS/database health, customer/browser checks and logs before updating the
   environment table and append-only deployment history in `RELEASES.md`.

No deployment ID or live success is asserted for v0.5.0. New provider, model,
worker, messaging or infrastructure charges are not introduced. Existing hosting
capacity and storage still have finite limits.

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
