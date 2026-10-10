# v0.4.3 — owner-only Data coverage

## Behavior and scope

The Data coverage dashboard and detailed feed diagnostics use the existing
server-authorized owner account boundary. Ordinary customer accounts, including
paid and complimentary accounts, cannot access `/api/sources` or
`/api/capabilities`. These routes return 401 for guests and 403 for non-owners.
Client-provided owner claims cannot grant access. An unconfigured owner fails closed.

The coverage navigation is hidden until `/api/session` confirms `is_owner`.
Signing out clears the panel, cached diagnostics, and coverage summary. Customer
search responses omit diagnostic source records but retain the same listing
results, totals, filters, source attribution, evidence, and generic freshness
warning. Hunts retain the same matching and review groups. The configured payment
entitlement still controls access to paid features.

Changed areas: `landwolf/main.py`, `web/app.ts`, `web/index.html`, API/browser
regressions and fixtures, PostgreSQL and hosted release check scripts, release
metadata, README, and framework documentation. Billing, authentication, Hunt
matching, database/schema, dependencies, and infrastructure were not changed.

## Candidate verification

Final candidate `0e4a27b619889a4fcf6650d2b0d5321f4e4bf3ed` passed
[all application gates](https://github.com/lupu-spec/Landwolf/actions/runs/37267053716),
[53 legacy tests](https://github.com/lupu-spec/Landwolf/actions/runs/37267053720), and
[release preflight](https://github.com/lupu-spec/Landwolf/actions/runs/37267053735).
The application run passed 368 backend tests, 9 frontend tests, 30 browser journeys,
disposable PostgreSQL integration and restore, packaging, and security scans.

Commands below run from `beta/` unless labeled otherwise. **Passed** means exit 0.
Hosted results are from the exact final candidate above.

| Command | Local result | Hosted result |
| --- | --- | --- |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed | Passed |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed | Passed |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | Passed; 26 Python modules | Passed |
| `npm run test:unit` | Passed; 9 tests | Passed |
| `.venv/bin/pytest -q -m 'not browser'` | Passed; 368 tests, 30 separately gated browser cases excluded | Passed |
| `.venv/bin/python scripts/check_postgres.py` | Not run locally; no disposable PostgreSQL service | Passed |
| `.venv/bin/python scripts/check_restore.py` | Not run locally; no disposable PostgreSQL service | Passed |
| `npm run build` | Passed | Passed |
| `.venv/bin/pytest -q -m browser` | Not run for this patch locally; browsers unavailable after previously documented archive download failure | Passed; 30 Chromium/WebKit journeys |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed | Passed |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable` | Passed; no findings | Passed |
| `npm audit --audit-level=moderate`; `npm run secrets` | Passed; no findings | Passed |
| `uv lock --check`; `npm ci` | Passed; version metadata only | Locked environment install passed |
| `PYTHONPATH=. .venv-legacy/bin/pytest -q` (root, isolated legacy environment) | Passed; 53 tests | Equivalent isolated legacy suite passed |
| `LANDWOLF_DATABASE_URL=sqlite:////tmp/landwolf-source-audit/verify.db .venv/bin/python -m landwolf.cli sync` | Passed; all 8 implemented listing feeds ready | Not run against live providers by CI |
| `git diff --check`; `git status --short` (root) | Passed; intended changes reviewed | Diff integrity passed |

The source sync used disposable SQLite, not production: MN 4, AR 0, TX 31,
USDA 19, Treasury 19, IRS 1, AK 170, MI 28 records retrieved. AR's empty result was
valid. This does not independently inspect production feed status or establish
complete upstream coverage. The existing daily maintenance automation remains enabled.
Research adapters were not changed; their checks were not repeated. The prior
FEMA HTTP 502 observation remains the latest recorded research-provider limitation.

## Resolved failures and limits

- New authorization regressions initially failed against the previous behavior.
  Test setup errors for required exemption timestamps and Hunt acreage bounds were
  corrected. The targeted suite and full final gates subsequently passed.
- Automated review found that the hosted check needed to retain its explicit
  staging billing-disabled requirement. The final assertion requires payments
  enabled in production and disabled in staging; the final candidate passed CI.
- Owner UI/API and paid-customer result parity are verified with isolated fixtures.
  Production browser probes use new unentitled test accounts without sending mail
  or making charges; no real owner or paid subscriber is impersonated.
- Physical-device testing and a complete accessibility audit were not performed.

## Production deployment

[PR #18](https://github.com/lupu-spec/Landwolf/pull/18) merged as
`b299190d271b4530a696871e10d96b4380323448`. Render deployment
`dep-db1j8i5g1s2s73af02s0` became live at 2026-10-05 05:24:17 UTC on the existing
production service. Pre-deploy logs confirmed schema 8 and retained accounts,
sessions and listings; application startup completed. No warning/error logs were
returned between 05:23:20 and 05:24:49 UTC. No database migration was added.

**Passed:** `.venv/bin/python scripts/check_hosted_staging.py --environment production`
in [hosted run 37267554161](https://github.com/lupu-spec/Landwolf/actions/runs/37267554161).
It verified the exact immutable runtime commit and v0.4.3, HTTPS and database
health, production payments enabled, mail disabled, the www redirect, guest
authentication, and four Chromium/WebKit journeys at 390px and 1440px. The live
customer account could not access either coverage endpoint (403), had no coverage
navigation, and retained normal session/reload/logout behavior. Search still
enforced unpaid membership (402); the account's Hunt list remained accessible.
No uncaught browser error or horizontal overflow was observed. One disposable
non-cohort account was retained. No payment was made and no mail was sent.

Customer/owner result parity and owner dashboard access passed isolated API and
browser tests, rather than production impersonation. Existing staging runtime
v0.4.1 is unchanged.

**Passed:** the inline Python HTTPS/version/health/image command in
`.github/workflows/live-smoke.yml`,
[run 37267834638](https://github.com/lupu-spec/Landwolf/actions/runs/37267834638).
It independently confirmed production v0.4.3 at the exact runtime commit above,
staging v0.4.1 at its existing commit, database/schema health, the expected fallback
image bytes for both sites, and the www HTTPS version endpoint. The release ledger
was synchronized to the staging branch as documentation only. Final local
`git diff --check` and `git status --short` passed with a clean tracked worktree
after synchronization; the deployment remains on the immutable runtime merge.
