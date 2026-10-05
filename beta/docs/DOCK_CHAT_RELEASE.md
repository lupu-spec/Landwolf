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

## Verification

Commands run from `beta/` except where noted. A pending or unavailable gate is not
a pass. Browser coverage includes Chromium and WebKit at 390, 834 and 1440px,
320px narrow-phone and short viewport checks, tablet rotation, actual Chromium
touch input, pointer dragging, keyboard routing, reduced motion, modal chat,
privacy clearing, and all existing customer/payment/owner regressions.

| Command | Result |
| --- | --- |
| `uv lock --check`; `npm ci` | Passed, exit 0; project version metadata only |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed locally, exit 0 |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed locally, exit 0 |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | Passed locally, exit 0 |
| `npm run test:unit` | Passed locally, 15 tests, exit 0 |
| `.venv/bin/pytest -q -m 'not browser'` | Passed locally, 411 tests, exit 0; 52 browser tests run separately |
| `.venv/bin/python scripts/check_postgres.py`; `.venv/bin/python scripts/check_restore.py` | Not run locally: no disposable PostgreSQL; required in hosted CI |
| `npm run build` | Passed locally, exit 0 |
| `.venv/bin/pytest -q -m browser` | Not run locally: Chromium/WebKit executables unavailable after prior invalid browser downloads; required in hosted CI |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed locally, exit 0 |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable` | Passed locally, exit 0 |
| `npm audit --audit-level=moderate`; `npm run secrets` | Passed locally, exit 0 |
| `PYTHONPATH=. .venv-legacy/bin/pytest -q` (root) | Passed, 53 tests, exit 0 |
| `LANDWOLF_DATABASE_URL=sqlite:////tmp/landwolf-dock-sources.db .venv/bin/python -m landwolf.cli sync` | Passed, exit 0; all 8 sources ready (zero current Arkansas rows) |
| `git diff --check`; `git status --short` (root) | Passed; intended changes only |

The initial TypeScript check found nullable DOM captures in nested dock functions;
validated local element references fixed those errors before the full gates.
The first two hosted browser runs exposed a pointer-focus scroll race: revealing a
partially clipped icon between pointer-down and release could cancel its click.
The dock now holds its position through the pointer gesture; direct Hunt and
Feedback clicks have explicit regression assertions. CSP rejected expression-style
Playwright polling predicates, which now use function predicates without weakening
the CSP. The guest-chat focus check now waits for asynchronous sign-out and its
intentional chat clear/collapse before reopening. Browser screenshots capture the
actual device viewport, avoiding misleading full-page fixed-panel placement.
An initial CSS write used the wrong working-directory prefix and made no CSS
change; the corrected write and formatting succeeded. Existing FastAPI/httpx/npm
warnings are unrelated. Browser emulation is not physical iPhone/iPad keyboard or
assistive-technology testing. Screenshots and browser behavior require review
before promotion. Existing navigation assertions now check the same full
accessible names because the requested visible labels are shorter.

## Deployment

Candidate only. Staging-first promotion, immutable commit identity, live HTTPS
and browser checks must pass before a production deployment is recorded here.
