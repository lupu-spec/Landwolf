# Mobile research keyboard repair — v0.12.1

Baseline: production v0.12.0 at `7b06ded06beca5bb4b54f3dcbaf83158e072c74f`,
Render `dep-db52sd7avr4c73f8u6l0`, observed live 2026-10-10 12:24:06 UTC.
The branch baseline is the subsequent documentation commit
`c0c9f728bd4921aa5a8f22cae0ec96b2adda610a`.

## Cause and behavior

The phone dock was fixed to the layout viewport instead of the visible viewport.
The property dialog used 92vh and a wrapping, sticky action header. Decision
inputs inherited 14.4px type, inviting iPhone focus zoom; New research also
opened the keyboard automatically. These combined to obscure navigation and
leave little space for research inputs and results.

`web/mobile-keyboard.ts` tracks bounded visual viewport resize/pan geometry,
with a layout-height fallback and no keyboard adjustment for pinch zoom. On
phones the dock becomes compact above the keyboard, with Done editing. Tablets
have a floating Done control. The native property dialog fits the visible area
and scrolls focused inputs below its compact header; its own Done and Close
remain reachable. Actions retain their titles and horizontally scroll on phones.
Touch controls stay stable between pointer down and click. Navigation and valid
research submissions dismiss the editor without clearing values; validation and
failed requests preserve normal correction and retry behavior. New research no
longer forces phone/tablet focus, and research inputs use 16px text.

Changes are browser layout/focus handling and regression/hosted checks, plus
release metadata. No dependency, API, calculation, schema, billing, account,
source, credential or infrastructure change is included.

## Verification

The two frontend viewport tests exercise iOS pan, Android layout resize, normal,
boundary, invalid/nonfinite geometry and pinch zoom. Six real Chromium/WebKit
browser/API/database cases exercise Property research and Decision research at
390/834/1440px: Done, entered-value preservation, valid submission, native invalid
input, provider/storage failure and retry, navigation/Close, visible modal header
and input, zoom and missing VisualViewport fallback. External research transport
uses explicit test fixtures; runtime never gains synthetic listings.

Physical iPhone/iPad/Android keyboard testing is **Not run**. Desktop Playwright
cannot show an OS keyboard; the new tests explicitly emulate viewport events.
Hosted checks additionally exercise the actual deployed focus/layout/Done controls
and normal real database/calculation/research journeys.

Final command results and observed deployments will be appended after gates.
