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
branch or network image reference. Both actual stylesheets are applied in their
original order to the same fixture-backed app. Computed properties, before/after
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
lower rounded edge, with maximum channel difference 2/255. The capture-stability
and bounded-diagnostics correction retains the exact image gate. Corrected hosted
results must establish whether that resolves the mismatch.

## Deployment constraint

No deployment has occurred. The connected Render account lists only `My Workspace`
associated with support.landwolf@gmail.com. The user selected a different workspace
but has not supplied its name/account. Do not select or deploy to the rejected
workspace. Obtain the correct workspace identity before service access; do not
change infrastructure, account access or billing to work around this gap.
