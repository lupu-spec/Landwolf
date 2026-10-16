# Appearance: silver, glass, light and dark

Use **Appearance** in the header on any screen:

- **Auto** follows the device's light/dark setting, including changes while the app is open.
- **Light** uses silver surfaces, pale inset fields and dark readable text.
- **Dark** uses graphite surfaces, dark inset fields and light readable text.

The same mode applies to sign-in, Explore forms/results/map controls, property
details and scenarios, Research, Hunt, Sources, Feedback, Membership, CRM,
owner finances, account dialogs and Romulus & Remus. Cards use rounded outlines,
subtle silver highlights and opaque readable inputs. Warning and source-health
colors retain their meaning. Source freshness thresholds are unchanged.

The preference is saved on this browser/device, across navigation, reloads,
sign-out and browser restarts. Open tabs follow the latest saved choice. Clearing
site storage resets it to Auto; blocked storage permits changes for the current
page only. It does not update account data or access. The initial appearance
loads before the main application to avoid a light flash when Dark is saved.

The supplied logo, property photos and geographic map tiles retain their original
colors. No photo is darkened or recolored as evidence. Printed research packets
use a light background. Mobile keyboard Done controls and dock behavior remain.

## Editing and verification

`web/graphite.css` owns palette tokens, frosted surfaces and outlines.
`web/styles.css` owns feature layouts and consumes the tokens; avoid hardcoded
white cards or navy text in new features. `theme-preference.ts` validates saved
choices and resolves Auto. `theme-init.ts` is the small blocking external bundle;
`theme.ts` wires the header, device-setting and cross-tab updates. No inline script
or CSP exception is needed and no dependency was added.

Run the repository gates plus `pytest -q -m browser tests/test_theme_browser.py`.
The appearance journeys exercise both modes across all primary workspaces in
Chromium/WebKit at phone, tablet and desktop widths, first paint before app
startup, persistence, device changes, cross-tab clearing, print, and unavailable
or malformed storage. Review their screenshots as well as assertions.

Keep these compatibility constraints when changing the finish:

- Preserve the established 16px mobile Research/decision inputs. Do not apply a
  shared `font: inherit` reset over their mobile font rules.
- The fixed phone dock lives inside the header: a filter, backdrop filter or
  transform on that ancestor can change its containing block. Keep the glass
  effect on the dock itself and allow account/appearance controls to wrap at
  large text sizes.
- Resize observers must schedule dock/map layout writes in an animation frame,
  coalescing repeated notifications. Keep the zero-browser-error, rotation,
  keyboard and 200% text-size checks; do not filter resize-loop errors.


## Shared header cascade (v0.15.1)

Header layout lives beside the glass dock in `styles.css`: one base rule plus
only tablet (640–1000px) and phone (≤639px) deltas. The previous 1150/1050/800px
header declarations were superseded by the dock base rule. Navigation retains
its effective responsive rules; earlier overridden font sizes and redundant
800px order/width/alignment/grid declarations were removed. `graphite.css`
continues to own the palette and narrow-screen appearance/wrapping overrides.
Do not collapse these intentional theme, breakpoint, print or keyboard rules.

`tests/test_header_css_browser.py` compares every computed property, pseudo-element
and bounding rectangle of the header tree against immutable approved v0.15.0
commit `55a35648140ffb3d3dead8c2e09a54d55dfc0e63`. It covers both browser engines,
guest/owner state, Light/Dark/Auto, breakpoint edges, large text, print and short
viewports. Phone/tablet/desktop header and dock screenshots must match byte for
byte within the same browser run. These are comparative screenshots, avoiding
platform-dependent golden fonts; both images are retained for review. Existing
mobile/dock/theme journeys remain the behavioral checks for keyboard/focus,
rotation, viewport handling, persistence and accessibility.

For shallow clones, first run from the repository root:
`git fetch --no-tags --depth=1 origin 55a35648140ffb3d3dead8c2e09a54d55dfc0e63`.
Then from `app/`, run
`.venv/bin/pytest -q -m browser tests/test_header_css_browser.py`.
Missing baseline objects fail the test. Do not move the baseline or accept an
image difference without reviewing and documenting a separately approved design.
