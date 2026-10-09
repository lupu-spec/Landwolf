# CRM administration and chat account help — v0.9.0 deployment verification

> For current contact-opening and mobile login behavior, see
> [the v0.9.2 mobile fix](CRM_MOBILE_FIX_RELEASE.md). Historical evidence follows.

## Candidate and scope

User authorized publication and staging/production deployment on 2026-10-06.
PR: https://github.com/lupu-spec/Landwolf/pull/25.
Published candidate `19c2b7cf42216efe1e2c7e0614b9d943dec266b3` has tree
`c45b8e86481d5dc044f894c6ab5dd4cf97ae2d9d`, exactly matching locally verified
candidate `2874377`. The connected GitHub API published the same tree after
command-line push failed because HTTPS credentials were unavailable.

Owner CRM adds manual contacts, profile corrections, trial reservations/grants,
complimentary access, suspension/restoration, session revocation and recovery
requests. Customer chat adds own-profile review/save and email-bound reset
requests; no deletion, identity override or owner-field mutation is exposed.
Behavior and changed source files are detailed in
[owner verification](CRM_ACCOUNT_ADMIN_RELEASE.md) and
[chat verification](WOLF_ACCOUNT_HELP_RELEASE.md). Schema 11 is additive.
No application patch was required by the final candidate verification.

## Required gates — passed

Hosted candidate run: https://github.com/lupu-spec/Landwolf/actions/runs/37418762391.
All commands below exited successfully on the published candidate. Run from
`beta/` unless specified. The lockfiles and runtime dependencies were unchanged
apart from the candidate's version metadata.

| Command | Result |
| --- | --- |
| `uv sync --frozen --dev`; `npm ci` | **Passed**, locked environments. |
| `.venv/bin/playwright install --with-deps chromium webkit` | **Passed** in hosted CI. |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | **Passed**. |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | **Passed**. |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | **Passed**. |
| `npm run test:unit` | **Passed**, 16 frontend tests. |
| `.venv/bin/pytest -q -m 'not browser'` | **Passed**, 468 tests, 68 browser cases deselected, two framework deprecation warnings. |
| `.venv/bin/python scripts/check_postgres.py` | **Passed**, disposable PostgreSQL integration including CRM/account help. |
| `.venv/bin/python scripts/check_restore.py` | **Passed**, exact row-digest pg_dump/restore across 29 tables in the disposable database. |
| `npm run build` | **Passed**. |
| `.venv/bin/pytest -q -m browser` | **Passed**, 68 Chromium/WebKit journeys; 335.81 seconds. New owner/chat cases cover 390, 768 and 1440px. |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | **Passed**. |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable` | **Passed**. |
| `npm audit --audit-level=moderate`; `npm run secrets` | **Passed**. |
| `git diff --check`; `git status --short` (repository root) | **Passed**, clean candidate. |

Separate legacy Test and Release Preflight workflows also passed:
37418762364 and 37418762381. The prior local legacy command
`PYTHONPATH=. /workspace/scratch/051463328da8/Landwolf/.venv-legacy/bin/pytest -q`
passed 53 tests. Prior local source sync and command results remain in the linked
reports; hosted gates resolve the prior local browser/PostgreSQL availability gaps.
The 48,666,210-byte browser artifact exceeded the workspace's 32 MiB download
limit, so no full artifact download or manual review of those screenshots was
claimed. Automated layout assertions passed.

## Additional live staging check

`.venv/bin/python /workspace/scratch/1546a3fb24bf/check_staging_account_help.py`
**Passed** against exact candidate v0.9.0: registration, own-profile persistence,
stale revision rejection, prohibited privilege fields, HTTP 405 deletion denial,
HTTP 403 owner-list denial, reset-recipient override rejection, unavailable-mail
response and logout/HTTP 401 after logout.

The first run **Failed** at logout because this temporary verification script
omitted the required JSON body. Its prior assertions passed. Adding `json={}`
made the full run pass without changing application code or weakening assertions.
Two synthetic example.com verification accounts were retained across these runs;
no real customer email was sent. The hosted browser smoke uses its own synthetic
account. No production customer was edited by these checks.

## Email delivery — not operational

The production environment had no mail-provider credentials: only the unrelated
pilot-invite email setting was present. Public session state reports email
delivery disabled. Gmail is connected to the assistant as the support mailbox;
this is not a runtime server credential and does not configure outbound delivery.
No matching provider-setup messages were found in a targeted mailbox search.

**Not run:** real reset email delivery and inbox-link completion. API tests prove
one-use, email-bound reset behavior using synthetic transport. Production reset
buttons remain disabled and guest requests report unavailable delivery. Enabling
real mail requires server-side provider credentials and a verified sender, followed
by a real mailbox test. No secret was requested in chat, invented or printed.

## Remaining limits

Physical devices, assistive technology and real payment transactions were not
exercised. Browser emulation is not a physical-device test. The workspace receives
a `Site Unavailable` HTML response for landwolf.ai, while the platform hostname
returns valid APIs; independent hosted checks verify the custom domain. Existing
source coverage limits remain. No external project is connected automatically.

## Observed deployments and live checks

| Environment | Commit | Render deployment | Live UTC |
| --- | --- | --- | --- |
| Staging | `19c2b7cf42216efe1e2c7e0614b9d943dec266b3` | `dep-db28igbbc2fs73flvjb0` | 2026-10-06 05:39:11.293174 |
| Production | `610457a303894f4b6f592387f489d5af309511c2` | `dep-db28k8uk1f9s739hmqc0` | 2026-10-06 05:42:47.601908 |

Both runtime trees are `c45b8e86481d5dc044f894c6ab5dd4cf97ae2d9d`.
`.venv/bin/python scripts/check_hosted_staging.py --environment staging`
**Passed** in run 37419507329; production equivalent **Passed** in run
37419788789. Each verified the exact version/commit, HTTPS and health, environment,
billing/mail mode, four Chromium/WebKit customer journeys and persistent-cookie,
cache-clear, browser-restart and logout behavior. Production checks used
landwolf.ai and verified www redirection. Staging research correctly reported
partial coverage. Downloaded staging evidence was visually inspected as a
contact sheet; automated assertions provide the detailed browser gate.

Direct platform API checks **Passed**: version 0.9.0/production/610457a, health ok,
payments enabled, mail disabled. The existing owner browser session survived
reload; the new CRM add/profile/account controls loaded. A previously requested
customer trial was reserved through the live owner UI using its default 90 days;
registration is still pending, so no active account was claimed and no email sent.
No customer identity appears in this repository report or the reusable guides.

Read-only aggregate database checks before/after returned 29/30 accounts and
30/31 CRM contacts, consistent with the single new production smoke account.
Counts are a sanity check, not a full historical data-integrity proof. The owner
coverage screen subsequently showed all eight imported feeds retrieval-current:
MN 4, AR 2, TX 31, USDA 19, Treasury 17, IRS 1, AK 170, MI 28. An earlier 7/8
summary was observed during the deployment's source refresh. Directory-only
sources and partial coverage remain explicitly labeled.

Render error-level log queries returned no entries for staging 05:39:11–05:40:01
and production 05:42:47–05:44:07 UTC. These are bounded observations.
The early ledger smoke run 37419788818 **Failed** because staging was already
v0.9.0 while its checkout's observed-release table still recorded v0.8.0. Its
production v0.8 check passed before promotion. The table is reconciled after
observing both deployments; the independent exact-release gates above passed.

## Visual packet verification

The combined 26-page guide is updated to observed v0.9.0 status. Separate guides
contain 18 customer-only pages, 12 owner pages and 10 generic L91 configuration
pages. They include pictures, compact flows and technical subtext, with no real
customer data. Generic configuration separates owner-UI settings, server secrets,
project backend integration and code/schema changes. Email remains labeled
unavailable. Render/build commands and checks: `python3 build_guide.py`,
`python3 build_audience_guides.py`, PDF page/text bounds checks and
`node --check /tmp/guide-check.js` for each generated offline HTML script —
**Passed**. Contact-sheet and representative full-page visual reviews completed.
