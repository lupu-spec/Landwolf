# v0.15.1 header CSS maintainability

Candidate PR: [#40](https://github.com/lupu-spec/Landwolf/pull/40).
Production remains on the completed v0.15.0 release until staged acceptance and
production promotion are recorded in RELEASES.md. This work does not repeat the
design release.

## Bounded change and cascade review

`web/styles.css` reduces `.site-header` from seven rules to three: base layout,
640–1000px tablet grid, and ≤639px phone layout. Base `display`, `height`, alignment
and bottom border move beside the existing dock base rule. Earlier header heights,
wrapping, spacing, padding and background declarations were always overridden by
that later rule. Earlier navigation font sizes were overridden by the shared
0.875rem rule. The 800px order/width/alignment duplicated the inherited 1050px
rule; the older two-column template was overridden later at the same breakpoint.

The remaining responsive navigation rules, `graphite.css` palette/wrapping,
print styles and mobile editing overrides are intentional and retained. No HTML,
TypeScript, runtime business logic, dependencies, schema, customer/CRM data,
credentials, billing configuration or entitlements change. Only the required
application/package release identity advances to 0.15.1.

## Regression contract

The immutable v0.15.0 production CSS is fetched by exact Git commit, not a mutable
branch or network image reference. Both actual stylesheets load in their
original order on independent fixture-backed pages and browser contexts. Computed properties, before/after
pseudo-elements and geometry are compared across 17 widths, guest/owner states,
Light/Dark/Auto, print, 200% text and a shortened viewport. Screenshots cover the
phone, tablet and desktop header/dock; exact byte equality is required. No masks,
changed baselines or difference tolerances are used. Existing full browser and
mobile/dock/theme behavior tests remain required.

Screenshots must stabilize to two consecutive identical captures, bounded at six
captures. Failure messages compare SHA-256 digests rather than printing PNG bytes;
computed-style mismatches retain full JSON artifacts with concise error output.
Complete snapshots are hashed inside the browser to avoid transferring all computed
properties over the browser driver for every breakpoint; no property is excluded.

## Evidence and retained failures

Local format/lint/types, 26 frontend and 572 backend/API tests, production build,
wheel/source packaging, Python/static/dependency scans, npm audit and secret scans
passed as recorded in VERIFICATION.md. Local browser setup failed due to OS package
permissions and truncated browser downloads; no local browser pass is claimed.

Initial hosted application run [38975787680](https://github.com/lupu-spec/Landwolf/actions/runs/38975787680)
passed format, lint, types, unit/API, disposable PostgreSQL and exact restore gates.
The full browser suite reported 127 passes and one Chromium header screenshot
mismatch. The job reached its 30-minute cancellation limit in the browser step; assertion
output included entire PNG byte sequences. Subsequent packaging/security steps were skipped. Archived
regression run [38975787790](https://github.com/lupu-spec/Landwolf/actions/runs/38975787790)
passed separately. This application run is **not a pass**.

Inspection of its retained approved/candidate PNGs found identical 390×76 image
sizes, identical computed properties, and six changed pixels around the logo's
lower rounded edge, with maximum channel difference 2/255. Stable recapture alone did not resolve the exact Chromium mismatch: run
38992401562 again reported 127 browser passes and that same one failure. It is not
a release pass. The comparison now loads baseline and candidate independently,
activating each page before measuring/capturing, so CSS replacement and previous
paint history cannot affect the result. Both computed styles and screenshots
remain exact; no masking or tolerance is introduced. A separate focused CI job
provides early feedback; the required full browser suite still runs all cases.
New hosted results must establish whether independent rendering resolves it.

## Deployment target and verification

The user confirmed the default Render workspace `My Workspace`
(support.landwolf@gmail.com) on October 17 UTC. Existing services are
`landwolf-premium-staging` and `landwolf-production`, retaining their current
branches, databases, payment configuration and manual deployments. No deployment
has occurred. Required corrected CI and then hosted staging acceptance precede
production promotion.

Hosted acceptance now checks exact hashes of both `styles.css` and `graphite.css`,
Auto device changes, and light/dark guest/customer header and dock screenshots in
Chromium/WebKit at phone and desktop widths. Existing authentication, CSRF,
owner/private routes, paywall, session restart/cache/logout and research checks
remain in place. No owner grants, charges, email sends or customer deletion are
part of these checks.
