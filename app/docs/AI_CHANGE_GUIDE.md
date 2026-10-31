# Making LandWolf changes with Codex or Chat

Read `/AGENTS.md`, `/app/AGENTS.md`, the feature guide and its tests before editing.
The active application is `app/`; `archive/legacy/` is recovery material with its
own dependencies and tests. Production is `main`; staging uses its existing
service/database and `staging` branch. A branch push alone is not deployment.

## Choose the smallest feature boundary

| Work | Start here | Verification |
| --- | --- | --- |
| Source age and thresholds | `web/source-health.ts` | `tests/source-health.test.mjs` |
| Source disclosures and timestamps | `web/source-list.ts` | `tests/test_source_list_browser.py` |
| Coverage filters/state/county view | `web/coverage.ts` | Source-list, trust and nationwide browser journeys |
| DOM and displayed source links | `web/dom.ts`, `web/source-links.ts` | UI types, source-list and existing browser suites |
| Public SEO | `landwolf/public_pages.py`, `web/assets/public.css`; see `PUBLIC_SEO.md` | Public document tests, no-JS/responsive browsers, hosted SEO acceptance |
| Shared light/dark appearance | `web/graphite.css`, `web/theme*.ts`; see `APPEARANCE.md` | Phone/tablet/desktop Chromium and WebKit, zoom, print |
| Shared header cascade | `web/styles.css`; see `HEADER_CSS_REFACTOR.md` | `tests/test_header_css_browser.py`, existing dock/mobile/theme suites |
| Base layouts and feature-specific UI | `web/styles.css`, individual feature modules | Existing corresponding browser tests |
| Sessions and recovery | `landwolf/auth.py`, `recovery.py`, `crm_access.py` | Security, session and recovery API/browser tests |
| Payments and trials | `landwolf/billing.py`, `trials.py`, `feedback.py` | Live/test isolation, consent, notice, cancellation and idempotency tests |
| Seller/broker sources and state filters | `commercial.py`, `craigslist_regions.py`, `web/source-filter.ts`; see `COMMERCIAL_SOURCES.md` | Commercial parser/API/state-isolation and responsive browser tests, explicit upstream checks only for configured licensed sources |
| Ingestion and provenance | `catalog.py`, `provider.py`, `national.py`, `trust.py` | Parser/invariant tests; explicit upstream checks only when needed |
| Research, Hunts, scenarios | `research*.py`, `hunt.py`, `analysis.py` | Ownership, assumptions, invariants and end-to-end handoffs |
| Owner finances and CRM | `finance*.py`, `crm*.py`; matching web modules | Role/ownership, cents/rounding, imports, forecast and CSV tests |

Keep `web/app.ts` as the composition/navigation layer. New feature state belongs
in its feature module and must be cleared on sign-out. Pure calculations should
accept explicit inputs and a controllable clock and have boundary/invalid tests.
Use textContent-based DOM helpers for provider/user text. Display-link allowlists
are not permission to fetch: server request allowlists have narrower path/query
contracts. Do not merge them into one permissive URL rule.

## Protected behavior

Preserve server-side authentication, owner pinning and billing entitlement checks;
CSRF/origin/host checks; HttpOnly revocable sessions; live-only Stripe checks;
explicit consent and feedback deadlines; at least seven days' email notice before
feedback-trial conversion; invited-pilot/CRM exemptions and cancellation behavior.
Do not enable payments or make real purchases as part of cosmetic verification.
Never copy production accounts or secrets into tests or commit customer exports.

Preserve last-good source snapshots, quarantine suspicious imports, source
attribution, validated coordinates, unknown values and user-entered assumptions.
Do not restore Saved or the removed Maximum Bid display from the archive.
No migration or database reset is required for this interface release.

## Recommended change workflow

1. Establish current branch and observed release identity; create a feature branch.
2. Define expected visible behavior, failure cases and compatibility constraints.
3. Change one feature boundary; keep refactors distinguishable in the diff.
4. Run all gates in `app/AGENTS.md` in order. Full UI changes need the full browser
   suite and disposable PostgreSQL/restore checks, not screenshots alone.
5. Review the final diff, update current help/docs and package-required assets.
6. Publish a PR and require successful hosted CI. Promote the verified source to
   the existing staging service, check it, then deploy the production commit.
7. Observe `/api/version` and `/api/health`, check hosted journeys and deployment
   logs, append actual version/commit/deploy/time evidence to `RELEASES.md`, and
   update its Current environments table to the same observed identities.

Report **Passed**, **Failed** and **Not run** precisely. An unavailable browser or
database is a verification gap. Never disable a check to ship a refactor. Prefer
small, tested module extractions over a framework rewrite or generic abstraction
that changes authentication, payment ordering or database transaction behavior.

Clock units matter in regression tests: Python Playwright numeric clock times
are seconds (or use an explicit UTC datetime), while JavaScript Date.now() is
milliseconds. Assert clock alignment before checking freshness boundaries.
