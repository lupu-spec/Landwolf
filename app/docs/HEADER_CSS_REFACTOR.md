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

The immutable approved v0.16.0 production CSS commit is
`168eb749ae4a2396b98b7b1e48a9862fc915ebb3`. CI fetches that exact object. Independent
pages load baseline and candidate stylesheets in the same order. Every header-tree
computed property, pseudo-element and bounding rectangle is compared across 17
widths, guest/owner states, Light/Dark/Auto, print, 200% text and short viewports.
Phone/tablet/desktop header and dock images must match exactly within one browser
run. The baseline is the current approved production release. No masks, excluded
properties or image tolerances are used. Captures must stabilize to two identical paints within six attempts; concise hashes avoid PNG
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
git fetch --no-tags --depth=1 origin 168eb749ae4a2396b98b7b1e48a9862fc915ebb3
.venv/bin/pytest -q -m browser tests/test_header_css_browser.py
```

Existing mobile/dock/theme tests continue to verify keyboard/focus, rotation,
viewport handling, persistence and accessibility. See VERIFICATION.md for exact
commands, results and retained local browser limitations.

## Reconciliation with the deployed SEO release

The first reconciled run 39183298613 found an exact phone dock difference despite
identical computed header styles. Retained images show changed page content behind
the translucent dock. The former v0.15 baseline targets workspace h1 and a JPEG;
the already deployed v0.16 SEO release uses h2 and WebP. Applying obsolete whole-page
styles to current markup changes the dock backdrop independently of this refactor.
The comparison now pins the actual approved production v0.16 commit above. This
retains those separately shipped SEO changes on both sides; it does not approve a
new design or tolerate differences. Every property and exact image check remains.
The earlier v0.15 results and failures remain recorded for traceability.

## Full-suite capture follow-up

Run 39183956547 passed the focused comparison (62 exact pairs) but the full suite
reported 141 passes and one Chromium guest-short header mismatch. Artifact
12158326786 was inspected: 35 pixels at rounded logo/control edges differed;
all computed styles and geometry matched. No release pass is claimed for that run.
The comparison now waits for font readiness and header image decoding, then uses
Chromium's deterministic compositor/renderer flags from its official
[command-line handler](https://github.com/chromium/chromium/blob/8e28e3b041d7634887b31d0245b8d8d734041283/headless/lib/browser/command_line_handler.cc).
BeginFrameControl is not enabled because normal Playwright frame ticks must continue.
No CSS, screenshot mask, excluded property, tolerance or retry-to-match is added.
Both focused and full suites must rerun. The verified source-flow release remains
independent; this refactor will not deploy until its complete gates pass.
