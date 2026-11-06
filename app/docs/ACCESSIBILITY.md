# Accessibility PDCA evidence and release plan

Target: WCAG 2.2 A and AA practical accessibility improvements, without a legal
certification or claim of complete conformance.

## Plan — baseline 2026-11-06

Observed production: 0.23.1, d6821ecbd6941823a855b6faf7b7a519967f56c2,
HTTPS /api/health reports ok. Candidate starts at repository main
5f35873665e1c15401f579b4e79da3ed41518e71.

Inspect public pages, sign-in/registration/recovery, search/list/map, property
and scenario dialogs, research, Hunts, feedback/membership and owner tools on
mobile and desktop in light/dark themes. Existing markup includes native dialogs,
labels and list/map switches; behavior and contrast still need measured checks.
No accessibility statement or axe regression suite exists in the baseline.

Countermeasures will follow observed audit failures, preserving authentication,
entitlements, source provenance, user data and the graphite/silver identity.
Acceptance: no WCAG-tagged axe violations in the covered states; keyboard-only
navigation, visible unobscured focus, dialog Escape/return focus, map list access,
error announcements, reduced motion and mobile reflow checks. Retain axe incomplete
results for human review. Automated success is not complete WCAG conformance.

Release boundaries: no schema changes; same candidate must pass repository gates,
hosted CI and staging acceptance before production. Keep existing infrastructure.
Prior compatible UI release is the rollback candidate; never reset customer data.

## Manual assistive-technology checklist — Not run

Record tester, date, exact runtime commit, browser/OS, assistive technology and
Passed/Failed for each item. Test NVDA/Firefox or Chrome and VoiceOver/Safari,
including iOS/Android physical devices where available.

- Follow skip link; read landmarks, heading hierarchy, page titles and active view.
- Complete sign-in, registration, recovery with keyboard and password manager;
  paste passwords; submit invalid/empty values and server failures. Confirm errors
  identify the field, explain correction and are announced without losing input.
- Traverse every dock item, filter, list page, source link and map/list switch;
  confirm focus is visible and not covered by the dock/chat/header.
- Open property details, Advanced scenarios and nested help; traverse controls,
  Escape each layer and confirm focus returns to the opener. No keyboard traps.
- Use List for every mapped or unmapped result, open details and source records;
  confirm no research action requires dragging, map gestures or visual coordinates.
- Complete research and Hunt creation/editing, empty results, failed requests and
  retries. Confirm loading, counts, errors and saved state announcements.
- Review owner CRM forms, tables, account actions, finances and coverage; verify
  role boundaries remain enforced. Do not perform destructive production actions.
- Test 200% text, 400% zoom/320 CSS-pixel reflow, custom text spacing, landscape,
  forced colors and reduced motion. Check dialogs and validation at each setting.
- Verify chart meaning is available in text/tables, meaningful image alternatives,
  contrast and focus in both themes, and touch targets/spacing on a physical phone.
- Follow Accessibility and support links. Review third-party maps, checkout and
  external source documents separately; do not infer their conformance.

## Do — candidate 0.24.0

Observed baseline axe failures: visible/accessibility-name mismatch on coverage,
CRM, chat and CRM statistics; invalid aria-pressed on the mobile results container;
non-focusable scrolling finance tables; insufficient contrast on dark map attribution.
Fixes preserve existing actions and expose readable names, region semantics, keyboard
scrolling and opaque theme-aware map credits. Main/skip-link targeting, result-count
announcements, research/auth error descriptions, reduced-motion programmatic scrolling,
forced-color focus and an accessible public statement are included.

Baseline public production scan: 12 page/viewport states; the desktop home launcher
failed label-content-name-mismatch. Authenticated baseline: four phone/desktop and
light/dark fixture journeys failed. Original JSON is retained in local audit evidence.
These fixture accounts do not establish authenticated production coverage.

Test development failures retained: initial exact research label was incorrect; next
attempt needed to switch from the property-prefilled coordinate mode to address mode;
one scan overlapped npm ci and lost its axe file. The motion unit test initially tried
to mock a missing window property; corrected with explicit isolated browser stub.
