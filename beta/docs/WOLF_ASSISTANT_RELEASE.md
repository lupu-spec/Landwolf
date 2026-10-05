# v0.6.0 — Romulus and Remus app guides

The requested **AI Chat with Romulus and Remus** toolbar control and persistent
collapsible chat introduce matching black/white twin wolf portraits. Romulus
provides steps; Remus explains controls and practical limitations. Help works on
sign-in, membership/paywall, every workspace tab and native account/property
modals. Guided walkthroughs navigate to and highlight actual controls for account
setup, property search, Hunts, location research and deal scenarios. Users perform
all form submissions and confirmations themselves.

## Scope and cost

This is a guide-based assistant with prepared answers and bounded, local
natural-language retrieval. It is not a live generative model. The chat discloses
that answers are prepared and matched on the device. It introduces no AI API,
token charges, dependency, backend service, endpoint, database table or schema
migration. Schema remains 9. Public-source research and existing payments are
unchanged. Answers explain the app, not property-specific investment advice.
Unknown questions offer relevant topics and the existing support email; ambiguous
queries ask the user to choose. Billing answers never claim a cancellation or
other account action was performed.

The reviewed guide covers getting started, account recovery, persistent sign-in,
search and missing results, Hunt saves and changes, maps, location research,
scenario assumptions, recorded research, comparisons, print packets, membership,
cancellations, feedback and support. Owner-only user exports and source diagnostics
are excluded from other users' answers and suggestions. Guide content is public
application code, not a security boundary; actual account data and APIs retain
server authorization. The assistant never reads private record or form values.

## Privacy and interface

Questions are limited to 600 characters. At most 12 turns remain in tab memory;
there is no message API, telemetry, browser storage or server history. Sign-out,
account entry, Clear chat and reload discard conversations. Messages render as
text nodes. Prepared navigation targets cannot execute user text or submit forms.
Tours have bounded navigation waits, retry/stop controls and stale-operation guards.

A single widget moves into the active native dialog so it remains usable in the
browser top layer. Collapse restores focus, Escape collapses chat before the
containing dialog, and new messages use an accessible log. The phone layout uses
VisualViewport when available to account for the keyboard, with a compact composer
for short viewports. Chat is excluded from printing. Black and white wolf SVGs use
the same silhouette and are included in the production wheel. They supplement the
existing LandWolf logo; the logo is unchanged.

## Verification

Run from `beta/` except where marked. Pending gates are not recorded as passes.

| Command | Result |
| --- | --- |
| `uv lock --check`; `npm ci` | Passed, exit 0; project metadata only, no dependency upgrade |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed locally, exit 0 |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed locally, exit 0 |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | Passed locally, exit 0 |
| `npm run test:unit` | Passed, 13 tests, exit 0 |
| `.venv/bin/pytest -q -m 'not browser'` | Passed, 411 tests, exit 0; 44 browser tests deselected for their separate gate |
| `.venv/bin/python scripts/check_postgres.py`; `.venv/bin/python scripts/check_restore.py` | Not run locally: no disposable PostgreSQL; required in hosted CI |
| `npm run build` | Passed locally, exit 0 |
| `.venv/bin/pytest -q -m browser` | Not run locally: previous browser downloads returned invalid archives; required in hosted CI |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed locally, exit 0; avatar assets included |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable` | Passed locally, exit 0 |
| `npm audit --audit-level=moderate`; `npm run secrets` | Passed locally, exit 0 |
| `PYTHONPATH=. .venv-legacy/bin/pytest -q` (root) | Passed, 53 tests, exit 0 |
| `LANDWOLF_DATABASE_URL=sqlite:////tmp/landwolf-wolves-sources.db .venv/bin/python -m landwolf.cli sync` | Passed, exit 0; eight implemented listing feeds ready in isolated verification database |
| `git diff --check`; `git status --short` (root) | Passed; intended files only |

The initial ambiguity example was a specific Hunt-research query, which correctly
matched one topic. A genuinely ambiguous single-word “save” request now offers
choices, and the test checks that behavior. An initial Ruff gate caught a long
browser-script string; adjacent string literals fixed it before the final gates.
The initial full backend run exposed an existing real-clock minute-boundary race
in the research rate-limit test. Its authentication clock is now held within one
bucket for that test; all 13 request assertions are preserved. The complete suite
then passed. Production rate limiting is unchanged.
Existing FastAPI/httpx and npm environment deprecation warnings are unrelated.
Avatar SVGs were rendered with Inkscape and visually inspected; its GTK warning
was nonfatal. Browser screenshots, keyboard behavior, modal accessibility and
download/payment/source regressions remain subject to the hosted browser gate.
Physical-device keyboard and assistive-technology testing are not performed.

## Deployment

Candidate only. Staging and production deployment are not claimed until the exact
version/commit and live HTTPS/browser checks are observed and recorded here.
