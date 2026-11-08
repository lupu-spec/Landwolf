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
