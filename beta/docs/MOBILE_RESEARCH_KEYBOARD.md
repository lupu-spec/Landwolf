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

## Passed candidate gates; deployment pending

The final code candidate is
`1a8cdb8f04d31de549ee4e6caefb7337f3cb641a`, tree
`855b310d07facb275316ddf33d9de75bb72327d9`. All three required PR workflows
completed successfully. [Full beta gates](https://github.com/lupu-spec/Landwolf/actions/runs/38057738782)
finished October 10, 2026 at 14:12 UTC. Each command below exited 0 in the
hosted locked environment after the final code change.

| Command (from beta unless noted) | Result |
| --- | --- |
| `uv sync --frozen --dev`; `npm ci`; `.venv/bin/playwright install --with-deps chromium webkit` | **Passed** |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | **Passed** |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | **Passed** |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | **Passed** |
| `npm run test:unit` | **Passed**, 18 tests |
| `.venv/bin/pytest -q -m 'not browser'` | **Passed**, 536 tests |
| `.venv/bin/python scripts/check_postgres.py` | **Passed**, disposable database only |
| `.venv/bin/python scripts/check_restore.py` | **Passed**, exact digests across 32 restored tables |
| `npm run build` | **Passed** |
| `.venv/bin/pytest -q -m browser tests/test_mobile_research_browser.py tests/test_dock_browser.py tests/test_wolf_assistant_browser.py` | **Passed**, 18 focused cases |
| `.venv/bin/pytest -q -m browser` | **Passed**, 108 unique cases |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | **Passed**, wheel and sdist validated |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable` | **Passed**, no findings |
| `npm audit --audit-level=moderate`; `npm run secrets` | **Passed**, no findings |
| Root `git diff --check`; `git status --short` | **Passed** |
| Root `PYTHONPATH=. pytest -q` | **Passed**, 53 legacy tests in run `38057738789` |
| Root `PYTHONPATH=. pytest -q tests/unit/test_deployment_preflight.py` | **Passed**, release preflight run `38057738787` |

Local format/lint/types, 18 frontend tests, 536 backend tests, build/package and
security checks also passed during preparation. Format/lint/types, frontend,
browser build, npm audit/secrets and diff integrity passed again after the final
focus-control edit. `uv lock --check` passed for version metadata. Local browser
executables, disposable PostgreSQL and the separate legacy pytest were unavailable;
the completed hosted checks above cover those environment gaps. Local physical
OS keyboard testing remains **Not run**.

Earlier candidates **Failed** on CSP-unsafe test wait expressions, overly broad
closed-chat hiding, fractional scroll bounds, WebKit touch-click cancellation
and a tablet acknowledgement checkbox moving during focus changes. These were
corrected without weakening assertions, removing tests or changing CSP. One
intermediate app.ts transfer was truncated; the tree comparison caught it before
any deployment. Full-file blob hashes and an exact local/remote tree comparison
were required for subsequent publication. The final full suite passed all these
existing and new paths, including login, chat, dock and simple/Advanced tools.

The final WebKit phone/tablet screenshots were visually reviewed: the compact
dialog header, Close, Done and focused cost field fit the emulated visible area.
No OS keyboard is drawn in these screenshots.

This candidate remains in [draft PR #35](https://github.com/lupu-spec/Landwolf/pull/35).
**Not run:** v0.12.1 staging deployment, exact deployed staging journeys and
production promotion. The subsequent source-maintenance request permits only
verified source repairs to production; none was confirmed. The mobile change was
therefore kept separate and not deployed by that maintenance run. Production
remains v0.12.0 at the baseline commit above. Source check evidence is in
[SOURCE_MAINTENANCE_2026_10_10.md](SOURCE_MAINTENANCE_2026_10_10.md).
