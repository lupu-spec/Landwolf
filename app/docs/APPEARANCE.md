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


## Header cascade maintenance

Header layout uses one base rule and tablet/phone deltas in styles.css. Earlier
superseded declarations are removed without changing intentional theme, print or
keyboard rules. The immutable approved CSS regression compares all computed
header properties and exact paired responsive screenshots. See
[scope and retained verification history](HEADER_CSS_REFACTOR.md).
