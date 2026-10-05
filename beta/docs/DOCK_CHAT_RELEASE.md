# v0.7.0 — glass navigation dock and responsive wolf chat

The text-heavy navigation becomes a compact frosted-glass icon dock. A compass
represents Explore, a document/magnifier Research, binoculars Hunt, stacked layers
owner-only Sources, a speech bubble Feedback, a card Membership, and the existing
black/white wolf portraits AI Chat. Short visible labels, full accessible names,
tooltips and the current-page indicator retain discoverability. The original
LandWolf wordmark and navy/white identity remain intact.

Hover proximity magnifies icons while their hit targets stay fixed. Swiping,
pointer dragging, the wheel and previous/next arrows browse the dock; cycling
wraps at either end. Arrow keys/Home/End move focus, and Enter activates a tool.
Moving through icons never selects a page or submits a form. Native pinch zoom is
preserved, wheel handling is scoped to the dock, and reduced-motion preferences
remove magnification and animated scrolling. The dock sits at the bottom on
phones and in the header on tablet/desktop, with content clearance beneath it.

Phone chat is a full-screen conversation sheet with background interaction/scroll
locking, keyboard focus containment and a visible collapse button. It does not
open the phone/iPad keyboard automatically. Tablet and desktop panels have larger
reading areas. A one-line horizontally scrollable topic strip and a compact
composer replace the tall blocks that crowded out messages. An expanding 16px
textarea, 48px send control, safe-area padding and visual-viewport sizing preserve
access to composing and closing controls. New answers start at the beginning of
the latest turn instead of jumping past the instructions. Draft text survives
rotation. About/privacy and support remain available in the expandable guide
information section. Chat content stays in tab memory with the same bounds and
sign-out/reload clearing; this continues to use disclosed prepared app guidance.

No model fees, paid dependency, endpoint, database migration, payment setting,
source entitlement or infrastructure change is introduced. Schema remains 9.

Implementation files: `web/navigation-dock.ts` and `web/dock-motion.ts` handle
motion/input; `web/index.html`, `web/styles.css` and `web/app.ts` integrate the
dock; `web/wolf-assistant.ts` handles responsive chat/focus; `web/help-guide.ts`
updates the support path. `tests/test_dock_browser.py`,
`tests/test_wolf_assistant_browser.py`, `tests/test_browser.py` and
`tests/dock-motion.test.mjs` cover the changed behavior. Runtime/project version
metadata moves to 0.7.0; dependency versions do not change.

## Verification

Commands run from `beta/` except where noted. The final candidate passed every required hosted gate in
[CI run 37296855330](https://github.com/lupu-spec/Landwolf/actions/runs/37296855330). Browser coverage includes Chromium and WebKit at 390, 834 and 1440px,
320px narrow-phone and short viewport checks, tablet rotation, actual Chromium
touch input, pointer dragging, keyboard routing, reduced motion, modal chat,
privacy clearing, and all existing customer/payment/owner regressions.

| Command | Result |
| --- | --- |
| `uv lock --check`; `npm ci` | Passed, exit 0; project version metadata only |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed locally and in final hosted CI, exit 0 |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed locally and in final hosted CI, exit 0 |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | Passed locally and in final hosted CI, exit 0 |
| `npm run test:unit` | Passed locally and in final hosted CI, 15 tests, exit 0 |
| `.venv/bin/pytest -q -m 'not browser'` | Passed locally and in final hosted CI, 411 tests, exit 0; browser tests run separately |
| `.venv/bin/python scripts/check_postgres.py`; `.venv/bin/python scripts/check_restore.py` | Passed in final hosted CI: PostgreSQL 18 and exact 23-table restore; not run locally (no disposable PostgreSQL) |
| `npm run build` | Passed locally and in final hosted CI, exit 0 |
| `.venv/bin/pytest -q -m browser` | Passed in final hosted CI: 52 tests, exit 0; not run locally (browser executables unavailable after invalid downloads) |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed locally and in final hosted CI, exit 0 |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable` | Passed locally and in final hosted CI, exit 0 |
| `npm audit --audit-level=moderate`; `npm run secrets` | Passed locally and in final hosted CI, exit 0 |
| `PYTHONPATH=. .venv-legacy/bin/pytest -q` (root) | Passed locally and in the final hosted legacy test run, 53 tests, exit 0 |
| `LANDWOLF_DATABASE_URL=sqlite:////tmp/landwolf-dock-sources.db .venv/bin/python -m landwolf.cli sync` | Passed, exit 0; all 8 sources ready (zero current Arkansas rows) |
| `git diff --check`; `git status --short` (root) | Passed; intended changes only |

The initial TypeScript check found nullable DOM captures in nested dock functions;
validated local element references fixed those errors before the full gates.
The first two hosted browser runs failed 14 checks and exposed a pointer-focus scroll race: revealing a
partially clipped icon between pointer-down and release could cancel its click.
The dock now holds its position through the pointer gesture; direct Hunt and
Feedback clicks have explicit regression assertions. CSP rejected expression-style
Playwright polling predicates, which now use function predicates without weakening
the CSP. The guest-chat focus check now waits for asynchronous sign-out and its
intentional chat clear/collapse before reopening. Browser screenshots capture the
actual device viewport, avoiding misleading full-page fixed-panel placement.
The next two runs passed all 46 existing/responsive-chat journeys but failed six
new dock cases. Feedback selectors now explicitly target the navigation instead
of matching another feedback control. Actual touch input exposed an implicit
pointer-capture handoff: the icon’s bubbling capture-loss event ended the swipe.
The track now ignores capture loss from descendants, and the 100px swipe must
scroll more than 75px. A new pointer-down also permits an immediate intentional
tap after a swipe. The final run passed all 52 browser journeys without relaxing
assertions. Phone/iPad/desktop dock and chat screenshots were visually reviewed.
An initial CSS write used the wrong working-directory prefix and made no CSS
change; the corrected write and formatting succeeded. Existing FastAPI/httpx/npm
warnings are unrelated. Browser emulation is not physical iPhone/iPad keyboard or
assistive-technology testing. Hosted Chromium/WebKit behavior and final screenshots were reviewed
before promotion. Existing navigation assertions now check the same full
accessible names because the requested visible labels are shorter.

## Deployment

PR #23 merged as `b35ef5dbded72e3553282616808f276d39ff7a6b`; its tree exactly
matches the final passing candidate `44348c839634fe3fb2d5811c96245edfb4d49305`.
Render marked staging `dep-db1nrodg1s2s73b2kmng` live at **2026-10-05 10:38:23 UTC**
and production `dep-db1nv7m0tbcc73bo70pg` live at **10:45:48 UTC**, both version
0.7.0 on the exact merged commit. Automatic deployment remains disabled; these
were explicit staging-first promotions of the existing services/databases.

- **Passed:** `.venv/bin/python scripts/check_hosted_staging.py --environment staging`
  in [run 37297750278, attempt 2](https://github.com/lupu-spec/Landwolf/actions/runs/37297750278/attempts/2).
- **Passed:** `.venv/bin/python scripts/check_hosted_staging.py --environment production`
  in [run 37297732989](https://github.com/lupu-spec/Landwolf/actions/runs/37297732989).
- Both observed exact immutable runtime identity, HTTPS and database health,
  expected billing mode (enabled only in production), protected owner APIs,
  four live Chromium/WebKit customer/chat journeys at 390/1440px, and persistent
  sign-in across browser restart/cache clearing plus explicit logout. Staging
  also exercised live listings, property research and scenario handoffs.
- No real customer/owner account was used and no payment was created. Each live
  attempt retained one disposable non-cohort test account. Live owner workflows
  were not exercised; owner authorization and export behavior passed isolated CI.
- Production backup/WAL completion was observed before promotion; disposable
  PostgreSQL restore passed. No migration, reset, payment configuration or
  infrastructure change occurred. Post-deployment error-log scans returned zero
  error-level entries in both environments.

**Retained failure:** staging attempt 1 passed identity/health and the complete
Chromium mobile journey, then timed out reopening a desktop property after
returning from Feedback. The unchanged build passed the full second attempt;
the initial transient timeout's cause was not established. No assertion, timeout
or runtime code was altered to obtain that pass. Production passed on its first
attempt. Local browser executables and physical iPhone/iPad/assistive-technology
validation remain unavailable; hosted browser coverage is not a physical-device
claim. The documentation-only release ledger is synchronized without redeploying.
