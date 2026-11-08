# Audit Desk footer release work order

Request: add a link at the bottom of landwolf.ai to the existing private Audit
Desk app and publish it. Use the software factory and retain logs.

Scope: one external footer link, accessible text, a new tab with opener/referrer
protection, HTTP and responsive browser regression checks, version 0.24.1.
No dependency upgrades, migrations, account changes or payment changes.

Factory workflow: existing LandWolf application gates plus Factory bridge gates
run on the pull request. Their GitHub Actions logs and browser artifacts are the
canonical command evidence. Use the actual L91 PDCA controller for release-gate
evaluation after CI. The static link does not need a paid generation/model run.

Acceptance: the public homepage footer contains exactly one Audit Desk link to
https://l91-audit-desk.secret-hen-4327.chatgpt.site, visible at tested responsive
sizes. The target remains private. Validate staging before production; observe
each live version/commit and record deployment IDs in RELEASES.md.

Local attempts (retained failures): format, lint and Python Ruff checks exited 0.
The local mypy executable exited 127 because the inherited virtual environment
has no Python executable. Retrying with that environment's Python also exited
127. These are not passes. Complete Python/browser/database/security gates must
run in the repository's clean hosted CI environment before promotion.

Git push exited 128 because this shell has no GitHub write authentication.
Use the connected GitHub API to publish the identical reviewed file changes.

Rollback: previous 0.24.0 runtime remains schema-compatible; this change adds no
database writes or migrations. Preserve existing services and databases.

PDCA correction: application CI 42439024989 passed 783 API/backend and 28
frontend tests, PostgreSQL integration and backup/restore, but its full browser
suite had 4 failed / 168 passed. Axe reported mobile target-size violations for
the direct footer support link after the new navigation link wrapped the row.
No deployment was attempted. The correction gives the direct support link a
44px minimum target height and asserts that size in responsive browser tests.
Run the four affected accessibility journeys first in CI so this failure is
caught early; retain all existing browser, package and security gates.

Local follow-up: recovered verification modules with the primary Python
interpreter; mypy, 783 backend/API tests, build/package and Bandit passed.
Node typecheck, 28 unit tests, build, dependency audit and secret scan passed.
Local pip-audit failed on unrelated shared-runtime packages (multidict, PyMuPDF,
VTK); do not treat that shared environment as the clean locked application.
An offline uv environment setup also failed on an uncached Ruff wheel.
Clean hosted security gates remain required for the corrected candidate.


## Final verification and publication log

| Result | Command / gate | Evidence |
| --- | --- | --- |
| Passed | Ruff format/check; npm run format:check; npm run lint; mypy landwolf; npm run typecheck | Final corrected CI |
| Passed | npm run test:unit; pytest -q -m 'not browser' | 28 frontend and 783 backend/API tests |
| Passed | python scripts/check_postgres.py; python scripts/check_restore.py | Disposable PostgreSQL integration and exact backup/restore across 49 tables |
| Passed | npm run build; pytest -q -x -m browser tests/test_accessibility_browser.py -k 'accessible_journeys and 390' | 4 affected mobile journeys |
| Passed | All existing focused browser commands; pytest -q -m browser; separate header-cascade job | 172 full browser tests plus focused runs and exact header comparison |
| Passed | python -m build; python scripts/check_package.py | Wheel and source package validation |
| Passed | bandit -r landwolf; pip-audit --local --skip-editable; npm audit --audit-level=moderate; npm run secrets | Clean hosted environment: no known vulnerabilities; static and secret checks passed |
| Passed | git diff --check; git status --short; git tree comparison | Staging and production source tree equality observed |
| Passed | Factory bridge: npm ci; npm run typecheck; npm test; npm audit --audit-level=moderate | 36 tests; retained GitHub logs |
| Passed | Read-only urllib checks of /api/version, /api/health and homepage footer in staging and production | Exact identities, link attributes and health observed |
| Failed | Initial .venv/bin/mypy and .venv/bin/python commands | Inherited local environment lacked Python; retained and later bypassed with current interpreter |
| Failed | uv sync --frozen --dev --offline | Ruff wheel absent from local cache |
| Failed | Local pip-audit in shared verification environment | Unrelated shared-runtime packages flagged; not relabeled passed. Clean locked hosted scan passed |
| Failed | Initial full browser CI 42439024989 | 4 target-size failures / 168 passed; fixed before deployment |
| Not run | Local browser engines, local disposable PostgreSQL and physical-device acceptance | Required browser/database gates passed in clean hosted CI; physical-device test remains outside this release |

Source df350b6bf191c65f9e69593fb025ab38e9987d52; tree f6d31da2b85ad3285c1fbea9caf5519ae8b71a0e. Final application run: https://github.com/lupu-spec/Landwolf/actions/runs/42441901616 . Factory run: https://github.com/lupu-spec/Landwolf/actions/runs/42441901649 . Failed first run: https://github.com/lupu-spec/Landwolf/actions/runs/42439024989 .

The actual L91 PDCA kernel recorded CHECK → DO after the failed application gate,
one new implementation revision, and ACT after fresh passing gates. The machine
record includes the evidence hash contracts and does not claim an independent human review.

Staging deployed as eeb25dfbea198d5ddf19f3e28395ed8af3a29d14 / dep-dbnv6t6417fc73erhi6g at 2026-11-08 03:59:53 UTC.
Production deployed as 9c8d08b229d343ff821e06b3cba322c1fb5e7398 / dep-dbnv8ojrjlhs739vt6c0 at 2026-11-08 04:03:40 UTC.
Live proof is retained in AUDIT_DESK_FOOTER_EVIDENCE.json. Both workloads returned
0.24.1 with the expected immutable commit and correct billing mode. One footer
Audit Desk link was present with target=_blank and rel=noopener noreferrer.
No customer records or funds were changed. Production app warning/error sample was empty.

Full command output remains in GitHub Actions logs; browser artifacts use the
repository's seven-day artifact retention. This permanent work order, failure
record, command summary, runtime identities and proof JSON remain in Git history.
Subsequent push-triggered/documentation CI runs are separate from the completed
candidate gate and are not claimed passed until observed. No extra deploy is
triggered by these documentation-only records (existing manual deploy settings).
