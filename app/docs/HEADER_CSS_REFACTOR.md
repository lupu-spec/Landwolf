# Shared header cascade consolidation

This follow-up retains the completed silver/glass appearance while reducing
`.site-header` from seven rules to three: base, tablet and phone. Base display,
height, alignment and border declarations move beside the effective dock rule.
Superseded header heights/spacing, earlier overridden navigation font sizes and
repeated 800px order/width/alignment/grid declarations are removed. Intentional
responsive navigation, graphite palette/wrapping, print and keyboard rules remain.
No HTML, TypeScript, backend behavior, authentication, billing or data changes are
part of the CSS refactor. Runtime/package identity advances to 0.18.0; dependencies
are unchanged. This candidate builds on the separately reviewed source-flow work.

The immutable approved v0.15.0 CSS commit is
`55a35648140ffb3d3dead8c2e09a54d55dfc0e63`. CI fetches that exact object. Independent
pages load baseline and candidate stylesheets in the same order. Every header-tree
computed property, pseudo-element and bounding rectangle is compared across 17
widths, guest/owner states, Light/Dark/Auto, print, 200% text and short viewports.
Phone/tablet/desktop header and dock images must match exactly within one browser
run. No masks, exclusions, changed baseline or tolerance are used. Captures must
stabilize to two identical paints within six attempts; concise hashes avoid PNG
output floods while full evidence is retained.

Earlier PR #40 CI failed: initial Chromium captures differed at six rounded logo
edge pixels. Stable recapture alone did not resolve it. Independent page rendering
did: the final focused run 38994952816 passed Chromium, but WebKit then failed to
load properties because repeated page reloads exceeded the real account's search
rate limit. This was an actual HTTP 429, not a CSS mismatch or missing fixture.
The comparison now paces paired owner reloads at least 2.2 seconds apart, leaving
the existing server limit untouched. It neither retries rejected requests nor
mocks authentication/search. All original comparisons and full browser suites stay
required. The application job budget rises from 30 to 45 minutes for the additional
comparison coverage; no gate is removed. Fresh CI must establish final success.

Production/staging deployment is not claimed here. Current identities and observed
release evidence belong in RELEASES.md. Fetch the baseline from the repository
root before a shallow-clone check; then from app run:

```sh
git fetch --no-tags --depth=1 origin 55a35648140ffb3d3dead8c2e09a54d55dfc0e63
.venv/bin/pytest -q -m browser tests/test_header_css_browser.py
```

Existing mobile/dock/theme tests continue to verify keyboard/focus, rotation,
viewport handling, persistence and accessibility. See VERIFICATION.md for exact
commands, results and retained local browser limitations.
