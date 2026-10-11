# Repository cleanup — October 11, 2026

Status: recovery archive verified; source reorganization undergoing required gates.
No production redeployment, database mutation, domain or secret change is requested.

The production Render service was renamed in place to `landwolf-production`.
Its ID, assigned URL, custom domains and live deployment are retained. The production
Blueprint has automatic synchronization paused. The retired original Render service
had automatic deployment from `main` enabled; that was disabled before changing
`main`, and its source was pinned to the original legacy snapshot.

The current project moves from its historical directory to `app/`, retaining
identical Python runtime modules, browser source/assets, Dockerfile, dependency
versions, database schema and runtime version. Package names are `landwolf` and
`landwolf-ui`; the package verifier follows the new distribution name. Docker build
settings, current workflows and documentation use the new path. Legacy application,
configuration and unsafe-to-reuse live verification workflows are archived under
`archive/legacy/`, with all 53 legacy regressions retained in a separate CI job.

The current supported branches are `main` and `staging`. Two dated archive branches
retain all 38 original tips plus the old Render service's buildable legacy tree.
The recovery commit's 36 distinct parents were independently read back from GitHub
and matched every original tip. Existing open PRs are superseded or archived without
merging unreviewed work. The complete branch/SHA index is `archive/BRANCHES.json`.

Existing database identifiers, platform-assigned hostnames and the local-development
SQLite filename retain their historical spelling as compatibility identifiers. They
are not product names or a release status. Renaming live connection identifiers or
DNS targets is outside this maintenance; no storage is recreated and no customer
record is changed. Historical deployment evidence remains dated and append-only.

## Verification

Pending: renamed-path full application/legacy gates, package and security checks;
read-only exact hosted identity/health/assets; final configuration/deployment-ID
comparison and archive/remaining-branch verification. A local moved-environment
mypy executable initially referenced the old path; `uv sync --frozen --dev --reinstall`
reinstalled the same locked versions and corrected its script paths.
