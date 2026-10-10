# v0.6.0 — Romulus and Remus app guides

> For current contact-opening and mobile login behavior, see
> [the v0.9.2 mobile fix](CRM_MOBILE_FIX_RELEASE.md). Historical evidence follows.

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

Run from `beta/` except where marked. Final candidate [CI 37289099883](https://github.com/lupu-spec/Landwolf/actions/runs/37289099883) passed all application gates on the exact tree promoted in PR #22. Every Passed command below exited 0; unavailable local gates were supplied by hosted CI.

| Command | Result |
| --- | --- |
| `uv lock --check`; `npm ci` | Passed, exit 0; project metadata only, no dependency upgrade |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed locally and in hosted CI, exit 0 |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed locally and in hosted CI, exit 0 |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | Passed locally and in hosted CI, exit 0 |
| `npm run test:unit` | Passed, 13 tests, exit 0 |
| `.venv/bin/pytest -q -m 'not browser'` | Passed, 411 tests, exit 0; 44 browser tests deselected for their separate gate |
| `.venv/bin/python scripts/check_postgres.py`; `.venv/bin/python scripts/check_restore.py` | Passed in hosted CI: PostgreSQL 18 integration and exact backup/restore row digests across 23 tables; not run locally (no disposable service) |
| `npm run build` | Passed locally and in hosted CI, exit 0 |
| `.venv/bin/pytest -q -m browser` | Passed in hosted CI, 44 Chromium/WebKit journeys, exit 0; not run locally (previous downloads returned invalid archives) |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed locally and in hosted CI, exit 0; avatar assets included |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable` | Passed locally and in hosted CI, exit 0 |
| `npm audit --audit-level=moderate`; `npm run secrets` | Passed locally and in hosted CI, exit 0 |
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
was nonfatal. Captured phone Chromium and desktop WebKit screenshots were visually reviewed.
The hosted gate passed modal/focus, short-viewport composer, offline answers,
XSS-as-text, bounded memory, guided navigation, sign-out clearing and owner-topic
checks, plus all existing download/payment/source browser regressions.
The first hosted browser run passed all 40 existing journeys. The four new
journeys passed the guest/customer, offline, modal, short-viewport and sign-out
checks, then failed because the test retained Create account mode before signing
in as the existing owner fixture. The test now selects Sign in; its assertions
are unchanged. The complete hosted rerun passed all 44 browser journeys before promotion.
Physical-device keyboard and assistive-technology testing are not performed.

## Deployment

[PR #22](https://github.com/lupu-spec/Landwolf/pull/22) merged as
`02293e8f8fe953c20ad01abb63b2f520723ac29a`. Staging and production serve that exact v0.6.0 commit.

| Environment | Deployment | Observed live UTC | Live verification |
| --- | --- | --- | --- |
| Staging | `dep-db1mpq9srm7s73cdvrgg` | 2026-10-05 09:25:51 | [Passed, run 37289871481](https://github.com/lupu-spec/Landwolf/actions/runs/37289871481) |
| Production | `dep-db1mru6gekts73ejko50` | 2026-10-05 09:30:22 | [Passed, run 37289869411](https://github.com/lupu-spec/Landwolf/actions/runs/37289869411) |

Both ran `.venv/bin/python scripts/check_hosted_staging.py --environment staging`
or `--environment production`, respectively, with the exact commit supplied by
`GITHUB_SHA`. Each passed version/commit/environment identity, HTTPS and health,
expected billing mode, four Chromium/WebKit customer journeys (390/1440px), the
new deployed chat question/answer, owner-only feedback user/export denial, and
persistent-cookie browser restart/cache-clear/logout checks. Production also
passed the www redirect. Production synthetic customers exercise the existing
paywall; no paid subscription or real customer account was created or modified.
One reserved example.com smoke account remains per environment, as the existing
smoke harness specifies. Full entitled flows and owner guides ran in isolated CI.

The existing production PostgreSQL 18 instance was observed available on its
paid plan with no external IP allowlist. Recovery logs show successful WAL
archival at 09:09:02 UTC; prior same-session backup-marker evidence is retained.
Schema 9 is unchanged, and no restore, billing setting or infrastructure tier was
changed. Physical-device keyboard/assistive-technology testing and live model
inference are not performed.

Additional hosted checks passed: `PYTHONPATH=. pytest -q` (53 legacy tests),
`PYTHONPATH=. pytest -q tests/unit/test_deployment_preflight.py`, and
`python scripts/deployment_preflight.py --environment staging` / `production` in
the configured static preflight workflow. These are compatibility/configuration
checks, not evidence of a new card charge or email delivery.

Changed implementation files are `web/help-guide.ts`, `web/wolf-assistant.ts`,
`web/app.ts`, `web/index.html`, `web/styles.css` and the two wolf SVGs; tests,
package/live-check scripts, version metadata and documentation accompany them.
