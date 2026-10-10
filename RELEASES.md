# LandWolf release log

This is the deployment ledger. A branch head is not proof of a live deployment.
Check each site's `/api/version` for the running version and immutable commit.

## v0.13.0 — private owner finances, candidate (not deployed)

Adds owner-only subscription collections, Stripe cash/fee reporting, business expense
records and confirmed Amex CSV imports, accessible graphs, three-month editable
scenarios and an evidence-linked growth playbook. Schema 13 is additive. Existing
accounts, billing, CRM, research and accepted trial terms are preserved. No bank
connection or guessed vendor cost is presented as verified. Production remains
v0.12.2 until full gates and exact hosted acceptance pass. See
[feature guide and verification](beta/docs/OWNER_FINANCE.md).

## v0.12.2 — mobile research navigation and preserved validation, live in both environments

Both research views fit navigation and dialog controls to the visible viewport,
provide Done, use 16px mobile inputs and preserve values through validation and
failed-request retries. Inactive address/coordinate inputs no longer block the
other mode's native validation; values remain available when switching back.
PR #35 merged as `f6cf068809bbc18ec9c8919156967a003e280b93`, whose complete
tree equals the staging-tested candidate. 536 backend, 18 frontend, 108 browser
and 53 legacy tests, PostgreSQL/32-table restore, build/package/security, exact
hosted staging/production session/privacy checks and six focused research journeys
per environment passed. Existing account, billing and CRM snapshots matched.
Schema 12, services, databases and production billing configuration are preserved.
Physical OS keyboards were not tested. See
[commands, observed deployments, failures and screenshots](beta/docs/MOBILE_RESEARCH_KEYBOARD.md).

## v0.12.0 — simple investment tools, live in both environments

The deal model starts with purchase/bid, expected sale, repairs/improvements and
closing costs. Advanced holds ranges, fees, financing, holding and targets while
retaining all values when collapsed. Research budget checks likewise show costs
and optional proceeds first. Invalid hidden inputs reveal the controls; guides,
bounded drafts and required zero-cost warnings agree with the new workflow.
The calculation API/formulas, schema 12, billing, trial policy, accounts, sources
and logo are unchanged. PR #34 promotes the identical tested/staged tree.
536 backend, 16 frontend, 102 browser and 53 legacy tests, PostgreSQL/32-table
restore, build/package/security and exact hosted staging/production checks passed.
See [command results, observed deployment and limits](beta/docs/SIMPLE_INVESTMENT_TOOLS.md).

## v0.11.1 — conditional self-service feedback trial, live in production

New self-service accounts may explicitly choose 90 days with day-30/60/90
feedback, saved payment method and separate billing consent. Missing feedback
requires at least seven days' notice before $29/month conversion; feedback or
online cancellation prevents conversion. All three completed check-ins end with
no automatic charge. Existing accounts, CRM grants and non-charging pilots retain
their terms. Signup, Membership, help, private reporting and Stripe wording agree.
Schema 12 is additive. Eligibility cutoff: `1791615052`, 2026-10-10 06:50:52 UTC.
536 backend, 16 frontend, 96 browser and 53 legacy tests, PostgreSQL/32-table
restore, build/security and exact staged/production hosted checks passed. The
final post-staging change corrects only a browser-test selector. See
[commands, observed deployment and limits](beta/docs/FEEDBACK_TRIAL.md).

## v0.10.3 — supplied header logo, live in both environments

The shared header on login and app screens uses the exact supplied JPEG, with
responsive contain sizing and a new asset URL. The no-photo fallback is preserved
byte-for-byte. PR #30 promotes the identical staging-tested tree. All 512 backend,
16 frontend, 90 browser and 53 legacy tests plus PostgreSQL/restore/build/security
gates passed. See [commands and evidence](beta/docs/LOGO_REFRESH.md).

## v0.10.2 — first-login property map repair, live in both environments

The initial map previously used only the first 12 list results. Production's
default page had no coordinates, although 30 matching locations existed. The map
now shows source locations across the filtered inventory independently of list
pagination, capped at 1,000 with an explicit count. Mobile map framing waits for
a visible container. Unlocated listings remain in the list. PR #29 promotes the
identical staging-tested tree; 512 backend, 16 frontend, 84 browser and 53 legacy
tests plus PostgreSQL/restore/build/security gates passed. Schema 11, billing,
accounts and source protections are unchanged. See
[cause, commands and verification limits](beta/docs/MAP_FIRST_LOGIN_FIX.md).

## v0.10.1 — CRM account categories and user statistics, live in both environments

Smoke-test records are automatically separated and hidden from default CRM lists
and CSV exports. Users excludes the owner and recognized tests; clickable Trial
users and Paid users counts filter customer membership. Additional categories
distinguish invitations, complimentary access and inactive plans. Reporting is
read-only and warns about stale stored billing data. The production aggregate job
found 5 users and 29 hidden tests on October 10. PR #28 promotes the identical
staging-tested tree; 510 backend, 16 frontend, 78 browser tests and PostgreSQL
restore/package/security gates passed. Schema 11, billing, Gmail and accounts are
preserved. See [rules, commands, live counts and limitations](beta/docs/CRM_REPORTING.md).

## v0.9.3 — support Gmail password recovery, live in production

Login-page and Romulus/Remus reset requests now send through
`support.landwolf@gmail.com`, with that same Reply-To. Reset links go only to the
requesting account. Verified two real emails and completed both one-use reset
flows, including old password/session rejection. PR #27 merged as
`e7baf8719fa6092013903cf1a53dd1cebcffbd07`, with the identical staging-tested tree.
Full gates passed 488 backend, 16 frontend, 74 browser and 53 legacy tests,
PostgreSQL/29-table restore, build/package and security. Both environments passed
exact-release hosted checks. Staging email remains disabled on its free plan.
Schema 11, billing, entitlements, source protections and existing accounts remain
unchanged. See [verification and operational limits](beta/docs/GMAIL_RECOVERY.md).

## v0.9.2 — CRM contact opening and mobile login chat, live in both environments

Open contact moves focus and the viewport to the contact editor, including loading,
retry and Back to contacts. Profile/account editing appears before long facts. Phone
login below 640 CSS pixels retains one floating chat launcher and hides the duplicate
chat-only dock. The current production Treasury repair is included. Schema 11,
permissions, billing and existing account data are preserved. Email delivery remains
disabled. Candidate gates passed 472 backend, 16 frontend, 74 browser and 53 legacy
tests, PostgreSQL/29-table restore, package and security. [PR #26](https://github.com/lupu-spec/Landwolf/pull/26)
merged as `356b64ad4a6d6694bd764dd0ec0ff0f6ee942774` with the identical tested
staging tree. See [commands, live evidence and limits](beta/docs/CRM_MOBILE_FIX_RELEASE.md).

## v0.9.1 — Treasury announced-date parser repair, live in production

The U.S. Treasury real-property page changed its identified unscheduled-sale label
from uppercase to title case (`Coming Soon...`). The parser now accepts that phrase
case-insensitively while continuing to reject other unrecognized date text. A direct
official-source sync recovered 21 Treasury records: 17 scheduled auctions and four
identified sales whose date is not announced. No schema, dependency, URL, billing,
entitlement, account, allowlist, snapshot or quarantine behavior changes. Production
deployment `dep-db3q1c5g1s2s73beear0` became live at 2026-10-08 13:56:13 UTC on
verified commit `1a49915940095830577c5d4ca7468fc714aaa035`. Hosted gates passed
472 backend, 16 frontend and 68 browser tests, PostgreSQL/29-table restore,
package and security. Custom-domain health reports v0.9.1 with payments enabled.

## v0.9.0 — owner administration and chat account help, live in both environments

Owner CRM account administration and customer chat profile/reset-request tools
are deployed. PR #25 merged as `610457a303894f4b6f592387f489d5af309511c2`, with
application tree identical to staging candidate `19c2b7cf42216efe1e2c7e0614b9d943dec266b3`.
Candidate gates passed 468 backend, 16 frontend, 68 browser and 53 legacy tests,
PostgreSQL/29-table restore, package and security. Both environments passed
exact-release HTTPS/health/browser/session checks. Schema 11 preserves existing
records. **Email delivery remains disabled; live reset mail is not operational.**
See [commands, deployment evidence and remaining setup](beta/docs/CRM_ACCOUNT_HELP_DEPLOYMENT.md).
The earlier candidate notes below are historical and superseded by this release.

## v0.8.0 — L91 LLC CRM and registration profiles, live in both environments

Adds private multi-project contact capture, owner filters, lifecycle/tags/follow-up,
notes, safe CSV downloads, and write-only project connector keys. Name and intended
use are required for new registrations; company, phone, job title, industry, role,
goals and email marketing are optional. Schema 10 adds CRM storage and preserves
existing account facts. No payment settings or paid dependencies change.
See [operation, categories, API and migration](beta/docs/L91_LLC_CRM.md) and
[verification record](beta/docs/L91_CRM_RELEASE.md). [PR #24](https://github.com/lupu-spec/Landwolf/pull/24)
merged as `7c3dc29889c1894bce34c55db29d1a591179bd66`, with the identical runtime
tree tested in staging. Final candidate gates passed: 429 backend, 15 frontend,
56 browser and 53 legacy tests, disposable PostgreSQL/26-table restore, build,
package and security. Both environments passed exact identity/HTTPS/health,
four live customer browser journeys and persistent-session checks.

## v0.7.0 — glass dock and responsive wolf chat, live in both environments

Compact icon navigation adds hover magnification and directional swipe, drag,
wheel, arrow and keyboard browsing. Romulus/Remus chat uses a full-screen phone
sheet and larger iPad/desktop panels with keyboard-aware controls and preserved
rotation drafts. [PR #23](https://github.com/lupu-spec/Landwolf/pull/23) merged as
`b35ef5dbded72e3553282616808f276d39ff7a6b`. Final candidate gates passed: 411 backend,
15 frontend, 52 browser and 53 legacy tests, PostgreSQL/23-table restore, build,
package and security. Both environments passed exact identity/HTTPS/health,
four live customer journeys and persistent-session checks. The first staging
attempt timed out reopening a desktop property; the unchanged build passed the
complete second attempt. Schema 9, payments, owner privacy and data sources are
preserved. See [commands, evidence and limits](beta/docs/DOCK_CHAT_RELEASE.md).

## v0.6.0 — Romulus and Remus app guides, live in both environments

Adds the AI Chat with Romulus and Remus toolbar control, collapsible help on every
screen, matching black/white twin wolf portraits and guided walkthroughs. Answers
use disclosed, reviewed local guidance without a paid model or message storage.
[PR #22](https://github.com/lupu-spec/Landwolf/pull/22) merged as
`02293e8f8fe953c20ad01abb63b2f520723ac29a`. All candidate gates passed:
411 backend, 13 frontend, 44 browser and 53 legacy tests, PostgreSQL/restore,
packaging and security. Both deployments passed four live browser journeys,
chat answers and persistent-session checks. Schema 9, payments and existing
owner-only data access are preserved. See [commands and limitations](beta/docs/WOLF_ASSISTANT_RELEASE.md).

## v0.5.1 — private feedback user list and CSV export, live in both environments

Feedback user details and CSV downloads require the existing owner administration
privilege. Private UI state is cleared on sign-out and authorization failures.
The new **Export users CSV** button downloads registered-user emails, roles and
pilot dates through the browser. Schema 9, payment architecture and dependencies
are preserved. [PR #21](https://github.com/lupu-spec/Landwolf/pull/21) merged as
`32b3fcf0ebbe6507e7f7142262cb94930b4439e8`; all candidate gates passed, including
411 backend, 9 frontend, 40 browser and 53 legacy tests, PostgreSQL/restore,
packaging and security. The exact staging-tested commit is live in production.
See [verification commands and limits](beta/docs/FEEDBACK_USERS_RELEASE.md).

## v0.5.0 — research decisions, live in staging and production

Private research goals/questions, Hunt briefs, cost stress/comparisons,
reconsideration history and print packets are live. [PR #20](https://github.com/lupu-spec/Landwolf/pull/20)
merged as `c333667f6a66b5dae870738387d01755f9ba485c`; the exact staging-tested
commit was promoted to production. All required CI passed: 395 backend, 9 frontend,
36 browser and 53 legacy tests, PostgreSQL/23-table restore, builds and security.
Each environment also passed four live browser journeys and persistent-session
checks. Schema 9 additively stores private research; payment gates, owner-only
coverage, accounts and existing infrastructure are retained. See
[commands, live evidence and limits](beta/docs/RESEARCH_DECISIONS_RELEASE.md).

## Current environments

| Environment | Site | Observed release | Runtime commit | Last deployment (UTC) |
| --- | --- | --- | --- | --- |
| Production | [landwolf.ai](https://landwolf.ai/) (`www` redirects here) | v0.12.2 | `f6cf068809bbc18ec9c8919156967a003e280b93` | 2026-10-10 20:28:08 |
| Beta | [Isolated beta](https://landwolf-premium-staging.onrender.com/) | v0.12.2 | `deafae9734a589718bf99912cdfab94164bdafa0` | 2026-10-10 20:16:52 |

## v0.4.0-beta.3 — Hunt result cards, live in isolated beta

- Removes per-listing fit badges and repetitive confirmed-criteria text. Cards
  retain specific missing-fact reasons only when a listing needs review.
- Adds source-approved thumbnails with the existing LandWolf default artwork for
  absent, disallowed or failed image links. The internal Hunt ranking and schema
  stay compatible. [Hosted beta run 116](https://github.com/lupu-spec/Landwolf/actions/runs/36483381497)
  passed browser, PostgreSQL, restore, package and security gates. Render deployment
  `dep-datddlfavr4c73d3pvng` became live at 2026-09-28 21:07:29 UTC; HTTPS
  version and health report the exact commit above and `ok`.

## v0.4.0-beta.4 — visible Hunt saving, live in isolated beta

- Labels the creation button “Save Hunt & view matches,” names the saved Hunt
  list, and confirms where a successful save appears. Editing uses “Save changes
  to Hunt.” The existing authenticated save API and criteria behavior are unchanged.
- [Hosted beta gates](https://github.com/lupu-spec/Landwolf/actions/runs/36500138618),
  root test and release preflight passed. Render deployment
  `dep-datft6dg1s2s7397ooq0` became live at 2026-09-28 23:57:02 UTC;
  HTTPS version/health and rendered save labels were observed.

## v0.4.0-beta.2 — simpler Hunt, live in isolated beta

- Three main choices: state, acreage band, and optional budget. Automatic names,
  quick starters, inline custom acreage, and results immediately after saving.
- Advanced criteria remain editable; cancel, retry, duplicate-submit protection,
  auction budget wording, and clear match labels support the full journey.
- Frontend-only behavior changes; schema v5 and existing Hunt/account data remain
  compatible. Hosted release run 112 passed browser, PostgreSQL, restore, package
  and security gates. Render deployment `dep-dat4ist9fdbs73flugo0` became live at
  2026-09-28 11:04:10 UTC; HTTPS version reports the exact runtime commit above.

## v0.4.0-beta.1 — live in isolated beta

- Adds authenticated Hunt criteria, deterministic fixed-price/auction fit, review gaps, revisioned edits, in-app change checks, and a schema-v5 additive migration.
- Nationwide state selection is supported against the existing partial connected catalog; no complete inventory or parcel-boundary claim. Opening a Hunt checks changes. Email and scheduled Hunt alerts are not enabled.
- Production stays on v0.3.3/schema v4. The isolated beta deployed `57663a20bd148525bd5515ce28c027e90751791a` as `dep-dasuvf0jo6nc73didk8g`; Render marked it live at 2026-09-28 04:41:23 UTC. Hosted browser, PostgreSQL, backup/restore, package, and security gates passed before deployment.
- See [Hunt beta scope](beta/docs/HUNT_BETA.md) and [verification](beta/docs/VERIFICATION.md).

## v0.3.3 — live in production and beta

- Repairs the live Texas GLO, U.S. Treasury, and IRS auction adapters after
  publisher markup changes; retains snapshot and URL/provenance safeguards.
- Makes manually initiated catalog refreshes initialize an empty local database,
  serializes public-source writes to avoid local SQLite contention, and gives
  bounded source-failure reasons in operations status.
- No database migration or dependency change.
- Staging and production both completed schema-v4 startup and Render reported the
  exact candidate commit live. The source refresh operates in the background;
  no subsequent source-refresh failure appeared in deployment logs.

## v0.3.2 — live in production and beta

- Use the owner-provided LandWolf “No Photo Available” artwork for property cards
  and detail images when a listing has no approved image or its image fails to load.
- Keep valid official source photos, the existing logo and the free beta unchanged.
- No database migration or dependency change.
- The beta [hosted gate](https://github.com/lupu-spec/Landwolf/actions/runs/36349823669)
  passed, including synthetic missing/failed image checks at 390px and 1440px.
  The wheel contains the image asset. Render reported both services live with
  application startup complete. The independent
  [HTTPS smoke check](https://github.com/lupu-spec/Landwolf/actions/runs/36350363603)
  verified production, `www`, and beta version endpoints and compared the
  downloaded fallback PNG to the owner-provided asset.

## v0.3.1 — live in production and beta

- Removes the navy Model Maximum Bid card and related copy from the simulation.
- Retains Median Net Profit, Probability of Loss and Median ROI as three white cards.
- Uses three columns on desktop and a single column on small screens.
- Keeps existing API response compatibility; no database change beyond the v0.3.0 migration.

## v0.3.0 — beta release; included in production v0.3.1

- Property evidence, publisher parcel identities, distinct sale events and source history.
- Suspicious source refreshes retain the last good inventory with warnings.
- State/county coverage and clearer research summaries; responsive navigation.
- Frameworks for evidence-based valuations, consent-based partners and source expansion.
  Those three frameworks are not active commercial services.
- Runtime version/commit endpoint and a footer link to this log.
- Existing logo and theme, free access, sign-in requirement and permanent Saved removal retained.
- Additive database schema v4 preserves accounts, sessions and existing listings.

Limits: partial public-source coverage; no nationwide MLS feed. IRS automation is
unavailable. Asking-price scenarios are hypothetical, and unknown costs stay zero
with warnings. Email delivery/recovery remains disabled pending verified sender setup
and live delivery tests. Physical-device testing and a complete accessibility audit
have not been completed. See [verification evidence](beta/docs/VERIFICATION.md).

## Deployment history

Append deployments below only after Render reports them live and HTTPS checks succeed.

| UTC | Environment | Version / commit | Deployment | Changes |
| --- | --- | --- | --- | --- |
| 2026-09-19 22:16:55 | Production | Unversioned / `5f65178540e24f10f49530dbd6ad14d6a9809264` | `dep-dangjc142hec73eebq10` | Permanently removed Saved, schema v3. Historical baseline; no retroactive release tag. |
| 2026-09-20 13:32:51 | Beta | Preview / `3f29a6ad3ae33ad490f55080b08fde5761953707` | `dep-danu0kjtqb8s73d5i2j0` | Isolated premium beta and additive schema v4; hosted Chromium/WebKit checks passed. |
| 2026-09-20 14:01:02 | Beta | v0.3.0 / `a8157056090bb39138d334da2eeb7ae59555abe9` | `dep-danudomk1f9s73a0jvu0` | Version endpoint/footer and ledger; all release gates and four hosted browser journeys passed. |
| 2026-09-21 15:00:38 | Beta | v0.3.1 / `f96208d897dc22c48f685237eb9477ba1c0b9aa8` | `dep-daokckdg1s2s738nf7c0` | Removes Maximum Bid display; retains three white metrics. Hosted simulation/browser checks passed. |
| 2026-09-21 15:05:01 | Production | v0.3.1 / `f96208d897dc22c48f685237eb9477ba1c0b9aa8` | `dep-daokek0ae00c73csh0ag` | Promotes premium trust/research features and three-card simulation. Additive schema v4; payments/email remain disabled. |
| 2026-09-27 20:57:20 | Beta | v0.3.2 / `9a738e4965277c0bc83a4dbb72cff0425e57a1d7` | `dep-daso5t7pn0mc7399i94g` | LandWolf no-photo artwork fallback; hosted Chromium browser gate passed. |
| 2026-09-27 21:00:18 | Production | v0.3.2 / `9a738e4965277c0bc83a4dbb72cff0425e57a1d7` | `dep-daso7c0473hc739772b0` | Promotes the exact beta-tested photo fallback revision; hosted HTTPS smoke check passed for production, `www`, beta and asset. |
| 2026-09-27 22:40:42 | Beta | v0.3.3 / `c5a5c6d6350441fadafc2c4625c3c7d279d0c6a4` | `dep-daspmbgjo6nc73cro8g0` | Repairs live official-source adapters and refresh diagnostics; schema startup complete. |
| 2026-09-27 22:43:03 | Production | v0.3.3 / `c5a5c6d6350441fadafc2c4625c3c7d279d0c6a4` | `dep-daspn8p7lnhs73a8mqk0` | Promotes the exact staging revision; schema startup complete and no source failure logged after restart. |
| 2026-09-28 04:41:23 | Beta | v0.4.0-beta.1 / `57663a20bd148525bd5515ce28c027e90751791a` | `dep-dasuvf0jo6nc73didk8g` | LandWolf Hunt beta with schema v5, deterministic fit/review results, in-app changes, and validated browser/PostgreSQL/recovery gates. |
| 2026-09-28 11:04:10 | Beta | v0.4.0-beta.2 / `d53dadee4f1e0b50d8513ea31e254e82479ea440` | `dep-dat4ist9fdbs73flugo0` | Three-choice Hunt setup, automatic names/results, advanced edit controls, mobile/desktop failure-and-retry coverage; all hosted release gates passed and HTTPS runtime version observed. |
| 2026-09-28 21:07:29 | Beta | v0.4.0-beta.3 / `19623b48ffc3ff4c97223feb8109cf7885b00cdc` | `dep-datddlfavr4c73d3pvng` | Plain Hunt result titles, specific review reasons, approved image previews and default-image fallback; hosted gates and HTTPS version/health passed. |
| 2026-09-28 23:57:02 | Beta | v0.4.0-beta.4 / `834f92ea276c29dd5c98fd5cc2de6b77621e3aea` | `dep-datft6dg1s2s7397ooq0` | Explicit save action, saved Hunt list and confirmation; hosted browser, PostgreSQL, restore and release gates passed; HTTPS version/health observed. |
| 2026-09-29 01:35:10 | Beta | v0.4.0-beta.5 / `af6fbcd8beec4e56e75c527ca27a7d3cf61fb82e` | `dep-dathb62d0e5s73c3uq90` | Durable Hunt saves independent of matching, verified saved-ID feedback and separate match retries. Full beta gates passed; deployed API and Chromium/WebKit create/edit/reload tests passed with exact IDs retained. |
| 2026-10-04 19:37:40 | Beta | v0.4.0-beta.7 / `4f52057d6499d420f6cfce6a9e97b1baa29d0dfe` | `dep-db1alfh42hec73epuo7g` | Investor feedback pilot, additive schema v7, required gates and four live HTTPS/browser journeys passed. |
| 2026-10-04 19:40:41 | Production | v0.4.0-beta.7 / `4f52057d6499d420f6cfce6a9e97b1baa29d0dfe` | `dep-db1amtou01pc73djnmm0` | Exact staging-tested commit promoted; schema v7, identity/health, www redirect and four live HTTPS/browser journeys passed. |
| 2026-10-05 05:24:17 | Production | v0.4.3 / `b299190d271b4530a696871e10d96b4380323448` | `dep-db1j8i5g1s2s73af02s0` | Owner-only Data coverage UI/API; identical eligible-customer search and Hunt results. Required gates and four live HTTPS/browser customer journeys passed; existing billing and schema 8 preserved. |
| 2026-10-05 05:47:01 | Production | v0.4.4 / `16b3c5818a5a095b1194fddf0abd46a82c1fb67c` | `dep-db1jj97avr4c73c850vg` | Renewable year-long sign-in; explicit logout/reset revocation retained. All gates and live Chromium/WebKit restart/cache/logout checks passed; billing, owner-only coverage and schema 8 preserved. |
| 2026-10-05 07:39:25 | Beta | v0.5.0 / `c333667f6a66b5dae870738387d01755f9ba485c` | `dep-db1l7sbncjis73f9qhpg` | Private research decisions, shared Hunt briefs, cost stress/comparisons, reconsideration and print packets. Schema 9; all required gates and four live browser journeys passed before promotion. |
| 2026-10-05 07:42:50 | Production | v0.5.0 / `c333667f6a66b5dae870738387d01755f9ba485c` | `dep-db1l9hh42hec73d7mj5g` | Exact staging-tested release promoted. HTTPS/version/health, live billing mode, four customer journeys and Chromium/WebKit restart/cache/logout checks passed; accounts, payment configuration and owner-only coverage preserved. |
| 2026-10-05 08:27:15 | Beta | v0.5.1 / `32b3fcf0ebbe6507e7f7142262cb94930b4439e8` | `dep-db1lua6gekts73efmfu0` | Owner-only feedback users and CSV download; all required gates, four hosted browser journeys, session persistence and live privacy/API checks passed before promotion. |
| 2026-10-05 08:30:53 | Production | v0.5.1 / `32b3fcf0ebbe6507e7f7142262cb94930b4439e8` | `dep-db1lvvu0tbcc73bg1re0` | Exact staging-tested commit promoted. HTTPS/version/health, live billing mode, four customer journeys, feedback user/export denial and persistent-session checks passed; schema 9 preserved. |
| 2026-10-05 09:25:51 | Beta | v0.6.0 / `02293e8f8fe953c20ad01abb63b2f520723ac29a` | `dep-db1mpq9srm7s73cdvrgg` | Romulus/Remus collapsible guide chat, toolbar control, black/white wolves and contextual walkthroughs. All required gates and four live browser journeys passed; no model fees, schema or payment changes. |
| 2026-10-05 09:30:22 | Production | v0.6.0 / `02293e8f8fe953c20ad01abb63b2f520723ac29a` | `dep-db1mru6gekts73ejko50` | Exact staging-tested release promoted. HTTPS/version/health, four live customer chat journeys, owner-only privacy boundaries, billing mode and persistent-session checks passed. |
| 2026-10-05 10:38:23 | Beta | v0.7.0 / `b35ef5dbded72e3553282616808f276d39ff7a6b` | `dep-db1nrodg1s2s73b2kmng` | Glass icon dock and responsive wolf chat; all candidate gates passed. Full live checks passed on unchanged rerun after an initial desktop property timeout. |
| 2026-10-05 10:45:48 | Production | v0.7.0 / `b35ef5dbded72e3553282616808f276d39ff7a6b` | `dep-db1nv7m0tbcc73bo70pg` | Exact staging-tested release; four live chat/customer journeys, privacy/payment boundaries, HTTPS/version/health and browser restart/cache/logout checks passed. Schema 9 and existing infrastructure retained. |
| 2026-10-05 12:50:41 | Beta | v0.8.0 / `476b683bca5bc56c67984a38c49298a63673f23c` | `dep-db1ppmqd0e5s738s9im0` | L91 LLC CRM, registration profiles, owner workspace and project intake; schema 10. All candidate gates and live HTTPS/health/browser/session checks passed before promotion. |
| 2026-10-05 12:54:15 | Production | v0.8.0 / `7c3dc29889c1894bce34c55db29d1a591179bd66` | `dep-db1prh7avr4c73d2o2ag` | Identical staging-tested runtime tree. Exact release/HTTPS/health, four customer browser journeys and persistent-session checks passed; accounts, billing settings and infrastructure preserved. |

| 2026-10-06 05:39:11 | Beta | v0.9.0 / `19c2b7cf42216efe1e2c7e0614b9d943dec266b3` | `dep-db28igbbc2fs73flvjb0` | All candidate gates passed; exact live identity/HTTPS/health, four browser journeys, persistence and additional account-help API checks passed. Mail remains disabled. |
| 2026-10-06 05:42:47 | Production | v0.9.0 / `610457a303894f4b6f592387f489d5af309511c2` | `dep-db28k8uk1f9s739hmqc0` | Identical staging-tested application tree; exact release, custom-domain HTTPS/health, four customer browser journeys and persistent sessions passed. Owner session/CRM inspected; billing retained. Mail setup remains. |
| 2026-10-08 13:56:13 | Production | v0.9.1 / `1a49915940095830577c5d4ca7468fc714aaa035` | `dep-db3q1c5g1s2s73beear0` | Repairs title-case Treasury `Coming Soon...` parsing. Hosted backend/browser/PostgreSQL/restore/package/security gates passed; exact custom-domain version/health and live payments verified. Schema 11, accounts, billing, allowlists, snapshots and quarantine protections preserved. |
| 2026-10-06 06:17:43 | Beta | v0.9.1 / `e32b7da81c3215a0b5f47a1fa4b75dac7327cd31` | `dep-db294evlot8c73eb8a30` | Interrupted mobile candidate; late history entry recorded October 9. Full 74-browser CI passed; not promoted. Superseded by combined v0.9.2 after production Treasury repair. |
| 2026-10-09 04:34:05 | Beta | v0.9.2 / `bb56ad94d19cd56714238c51a701e8c3824ca75e` | `dep-db46ss60tbcc73dbpj2g` | Combined mobile contact/chat fixes and current production Treasury repair. Full gates plus hosted exact-release HTTPS, browser and session checks passed. |
| 2026-10-09 04:42:04 | Production | v0.9.2 / `356b64ad4a6d6694bd764dd0ec0ff0f6ee942774` | `dep-db470mrbc2fs73arhgh0` | PR #26, identical staging-tested tree; Render live and exact runtime version/health observed. Full gate and live evidence in CRM_MOBILE_FIX_RELEASE.md. |
| 2026-10-10 02:53:44 | Beta | v0.9.3 / `29386436e5588889c0e37da418050f7e51980a99` | `dep-db4qgqlckfvc73ft49n0` | Gmail-capable runtime; staging email disabled. Superseded only to update the hosted smoke expectation for enabled production delivery. |
| 2026-10-10 02:56:09 | Beta | v0.9.3 / `5fa9f2552ea854292dc15077d2a9417dba022aa2` | `dep-db4qi4flk1mc73fm0r00` | Identical runtime; hosted smoke now requires production email enabled and staging email disabled. Full final gates and hosted staging journeys passed. |
| 2026-10-10 03:13:09 | Production | v0.9.3 / `e7baf8719fa6092013903cf1a53dd1cebcffbd07` | `dep-db4qq25ckfvc73fu2fc0` | PR #27, identical verified staging tree. Gmail enabled with the owner-saved credential. Exact health/version, hosted browser checks and both real reset-email flows passed. |
| 2026-10-10 03:36:35 | Beta | v0.10.0 / `7e790095fec952c991d9e19c644bb522f65a2d68` | `dep-db4r4vflot8c73cnckeg` | CRM account categories and customer membership statistics. Not promoted: read-only production audit identified 12 older test identities for inclusion in the next revision. |
| 2026-10-10 03:39:02 | Beta | v0.10.1 / `24dee28c3fa2d05de1b1951767b1fa37fcbbc5a2` | `dep-db4r645ckfvc73fv9qi0` | Adds confirmed legacy verification identities to conservative test classification. All final gates and exact staging customer browser checks passed. |
| 2026-10-10 03:49:25 | Production | v0.10.1 / `a3998b525530a845dedd66b52c401c0cb50b7d51` | `dep-db4rb4nlot8c73co0940` | PR #28, identical staging-tested tree. Exact hosted browser checks and read-only CRM job passed; 5 users, 29 test records hidden by default. Billing snapshot age is disclosed. See CRM_REPORTING.md for command evidence and limits. |
| 2026-10-10 04:28:34 | Beta | v0.10.2 / `bc1237f79a335a34dce133c502666f5157ce8540` | `dep-db4rtdflk1mc73fqbuig` | Map inventory independent of list pagination and visible-map sizing. Superseded by test-only verification refinements below. |
| 2026-10-10 04:29:30 | Beta | v0.10.2 / `df7854b8a3f125c7b4c5e6ed7c8736fbf28ae881` | `dep-db4rttijnfac738ail40` | Identical runtime; browser regression explicitly selects Sign in after registration/logout. |
| 2026-10-10 04:30:22 | Beta | v0.10.2 / `e10111c5c9030bb478c2175923fcede22dcbd640` | `dep-db4ru71rn11c73d1otp0` | Identical runtime; hosted verification now asserts marker intersection with visible map. Exact HTTPS/browser checks passed on live source inventory, including 30 mapped locations beyond the unlocated first list page. |
| 2026-10-10 04:40:48 | Production | v0.10.2 / `255fd1d9b8969e6c1c352188afca8e8d1669dd56` | `dep-db4s35nlot8c73cqeh3g` | PR #29, identical tested staging tree. Separates map inventory from list pagination and fixes hidden-map framing. Full gate and deployment evidence in MAP_FIRST_LOGIN_FIX.md. |
| 2026-10-10 05:14:29 | Beta | v0.10.3 / `536d83a2e74075aa85dcdd4438b6554e3bdc03d9` | `dep-db4sis5ckfvc7383rs2g` | Exact supplied header logo; fallback unchanged. Full gates and hosted staging verified. |
| 2026-10-10 05:26:16 | Production | v0.10.3 / `886906372f809c07277fb35b7f7f2cd2fddf85e9` | `dep-db4sogl9fdbs73ap63lg` | PR #30, identical staging-tested tree. Exact logo and fallback verification in LOGO_REFRESH.md. |
| 2026-10-10 06:19:36 | Beta | v0.11.0 / `bae62d8bc7c152571c8dff3a31b401d2659dda0f` | `dep-db4thcvlk1mc73fvrngg` | Conditional self-service feedback trial; billing/mail stay disabled. Full 536/16/96/53 tests, 32-table restore and hosted exact-release checks passed. Not promoted: follow-up preserves later owner pilot invitation UI when a self-service trial history exists. |
| 2026-10-10 06:28:14 | Beta | v0.11.1 / `042fad2e1d9c585d9a463bb6568c3b97bfcf827a` | `dep-db4tlglckfvc7387jgq0` | Later owner pilot invitation takes precedence over trial history. Exact staged HTTPS/browser checks passed; billing, mail and trial offer remain disabled. |
| 2026-10-10 06:51:38 | Production | v0.11.1 / `a8e66152e753ccdd3fa96821bc32f6c944e8d25f` | `dep-db4u0jid0e5s73dgdt7g` | PR #33 after all final gates. Same staged application code plus corrected browser selector. New-account cutoff enabled; schema 12, account/billing/pilot counts, public terms, email and live billing verified. Hosted production privacy/paywall/session checks passed. |
| 2026-10-10 12:20:08 | Beta | v0.12.0 / `e062b5386d8a9d672af462594c0b29d524a3c638` | `dep-db52qe2d0e5s73e0hblg` | Four basic deal inputs and optional Advanced; research budgets simplified. Full final gates and exact staged HTTPS, real calculation/research, browser/privacy/session checks passed. |
| 2026-10-10 12:24:06 | Production | v0.12.0 / `7b06ded06beca5bb4b54f3dcbaf83158e072c74f` | `dep-db52sd7avr4c73f8u6l0` | PR #34, identical tested/staged tree. Exact production identity, database health, four basic input HTML, billing/email/trial flags and hosted browser/privacy/session checks passed. Schema 12 and existing architecture retained. See SIMPLE_INVESTMENT_TOOLS.md. |
| 2026-10-10 20:02:17 | Beta | v0.12.1 / `a2ee4071b305efc0f444b1b38f03706d2b0255f7` | `dep-db59irqjnfac739mufp0` | Initial mobile keyboard repair; full candidate gates and exact standard staging research/navigation/session checks passed. Additional acceptance exposed inactive-field native validation; superseded by v0.12.2 before production. |
| 2026-10-10 20:16:52 | Beta | v0.12.2 / `deafae9734a589718bf99912cdfab94164bdafa0` | `dep-db59puflot8c73e70rq0` | Inactive inputs disabled without losing values. Full final gates, six focused Chromium/WebKit research journeys and standard exact hosted/session checks passed. One rate-limited sign-in rerun passed in the normal window. |
| 2026-10-10 20:28:08 | Production | v0.12.2 / `f6cf068809bbc18ec9c8919156967a003e280b93` | `dep-db59v7lckfvc739fkme0` | PR #35, entire tree identical to staging. Exact production health/billing/email/auth/privacy/session and six focused both-research-view journeys passed. Existing accounts/billing/CRM digests match; temporary audited test access revoked. Physical OS keyboards not run. See MOBILE_RESEARCH_KEYBOARD.md. |


## Version and promotion rules

- Use `MAJOR.MINOR.PATCH`; use `-beta.N` for future unreleased beta iterations.
- A version identifies one runtime revision. Never reuse it for changed runtime code.
  A production promotion may use the exact version/commit already tested in beta.
- Bump `landwolf/version.py`, Python/npm metadata and their lockfile project versions
  together; tests enforce agreement. Do not upgrade dependencies as a side effect.
- Before promotion: run required gates, review migration/recovery compatibility,
  verify backup availability and test the candidate in beta.
- Record version, immutable runtime commit, UTC time, Render deployment ID, changes,
  verification evidence and limitations for every push that becomes a deployment.
- Update the current-environment table only after observing the live release.
  Documentation-only ledger commits are not new runtime releases.
- Preserve history; append rollbacks as new events. Schema v4 is incompatible with
  the old schema-v3 image. An old-image rollback requires a coordinated database
  restore and reconciliation of writes since the backup; prefer a tested fix forward.
- Keep this canonical ledger on `codex/landwolf-premium-staging` and synchronize it
  with `codex/landwolf-beta-rebuild` at promotion. Do not infer deployment from Git.


## v0.4.0-beta.5 — Hunt save durability, live in isolated beta

- Save preferences before optional matching, preserving the saved Hunt if source
  validation or match storage fails. Storage errors are still reported as failures.
- Verify saved IDs through the account list, keep confirmation visible, and retry
  matching separately. Add database, failure-injection and mobile/desktop regressions.
- Existing schema v5 and production remain unchanged. [Beta gate run 36507987782](https://github.com/lupu-spec/Landwolf/actions/runs/36507987782), root tests and static preflight passed.
- Render marked `dep-dathb62d0e5s73c3uq90` live at 2026-09-29 01:35:10 UTC.
  [Live diagnostic 36508680217](https://github.com/lupu-spec/Landwolf/actions/runs/36508680217)
  verified HTTPS version/health, all five acreage bands, fresh-login persistence,
  and Chromium/WebKit create, edit and reload persistence against the exact runtime commit.
- See the [complete command results, retained failures and limits](beta/docs/HUNT_SAVE_VERIFICATION.md).
  Browser probes wait for session initialization; early-navigation races and physical-device testing are not covered.

## v0.4.0-beta.7 — historical candidate status before the rollout below

- Invitation-only three-calendar-month investor access, explicit consent, required
  in-app surveys, owner reporting and additive schema v7.
- Calendar expiry, seven-day capped survey grace, server-side access rules and
  session-idle preservation covered by local API/unit tests.
- Local non-browser, package and security gates passed; browser and disposable
  PostgreSQL/restore gates remain outstanding. No live deployment ID exists for
  this candidate. Existing observed environment rows above remain historical.
- See `beta/docs/INVESTOR_PILOT.md` and the dated verification entry.

## v0.4.0-beta.7 — live in staging and production

- Published and merged [PR #11](https://github.com/lupu-spec/Landwolf/pull/11).
- [Candidate gates](https://github.com/lupu-spec/Landwolf/actions/runs/37228598183) passed: 315 API, 28 browser and 9 frontend tests; PostgreSQL cohort transactions and 19-table restore; package and security checks.
- The exact commit above passed four live browser journeys in [staging](https://github.com/lupu-spec/Landwolf/actions/runs/37228923125) before production deployment, then four in [production](https://github.com/lupu-spec/Landwolf/actions/runs/37229118822).
- Invitation-only access lasts three calendar months, with required in-app surveys. Payments and email delivery remain disabled; no real investor was enrolled.
- [Command results, retained failures and operational limits](beta/docs/INVESTOR_PILOT_RELEASE.md).

## v0.4.0 — live-billing candidate, not yet deployed

- Adds live-only Stripe Checkout, a customer portal, signed webhook reconciliation,
  server-side paid entitlements and private marketing-pilot reservations.
- Reuses the approved $29/month and $299/year live recurring prices. No automatic
  pilot conversion, no testing charges, and no sandbox runtime credentials.
- Additive schema v8 preserves accounts, sessions, Hunts and feedback records.
- Deployment and live checkout/webhook verification remain pending. The observed
  environments and append-only deployment history above have not been changed.
- See `beta/docs/LIVE_BILLING.md` for configuration, rollback and verification gates.


## v0.4.2 — source recovery and production wording

- Production runtime `3f395b4a546c806d7eacd04229f3ac6a1f510659`,
  Render deployment `dep-db1ir2lg1s2s73ad5tig`, live 2026-10-05 04:55:21 UTC.
- Repairs MnDOT empty-sale sections, Treasury undated teasers and invalid sale
  markers, and IRS external promotions; preserves source validation/quarantine.
- Removes obsolete customer-facing product labels. Completed staging features
  already existed in the production baseline; unfinished integrations stay inactive.
- Payment logic/configuration, accounts and schema are preserved. Startup and
  pre-deploy checks passed; no data migration, reset or infrastructure change.
- [Final CI](https://github.com/lupu-spec/Landwolf/actions/runs/37265161046) passed
  all gates: 364 backend, 9 frontend and 30 browser tests, disposable PostgreSQL
  and restore, package/build and security. Legacy tests and preflight also passed.
- Eight implemented listing adapters passed a separate live-source sync; FEMA
  still returns HTTP 502. Production source-state rows are not independently
  inspected; startup schedules the existing automatic source refresh.
- Daily source maintenance is enabled for around 08:00 America/Chicago.
- Live HTTPS checks run independently on this ledger update. See
  `beta/docs/VERIFICATION.md` for exact commands, retained failures and limitations.

The staging environment row was reconciled with its existing Render deployment
`dep-db1g20ou01pc73e9dbi0`; staging was not redeployed for this production patch.

## v0.4.3 — owner-only Data coverage

- Production runtime `b299190d271b4530a696871e10d96b4380323448`,
  Render deployment `dep-db1j8i5g1s2s73af02s0`, live 2026-10-05 05:24:17 UTC.
- Data coverage navigation and detailed feed diagnostics use the existing
  server-authorized owner boundary, including direct API requests. Sign-out clears
  cached diagnostics. Paid and complimentary access alone do not grant admin rights.
- Search listings, filters, totals, attribution, evidence and Hunt matching remain
  available under the existing entitlement rules. Generic freshness warnings remain.
- [Final CI](https://github.com/lupu-spec/Landwolf/actions/runs/37267053716) passed
  368 backend, 9 frontend and 30 browser tests; PostgreSQL/21-table restore,
  packaging and security. Legacy tests and static release preflight passed.
- [Live release checks](https://github.com/lupu-spec/Landwolf/actions/runs/37267554161)
  passed exact identity, HTTPS/database health, billing mode and four Chromium/WebKit
  customer journeys. No real subscriber/owner account or payment was used.
- Existing production infrastructure, schema 8 and payment architecture were
  preserved. Staging remains on its previously observed runtime and is not redeployed.
- [Exact command results, evidence and limits](beta/docs/OWNER_COVERAGE_RELEASE.md).

## v0.4.4 — persistent sign-in

- Production runtime `16b3c5818a5a095b1194fddf0abd46a82c1fb67c`,
  Render deployment `dep-db1jj97avr4c73c850vg`, live 2026-10-05 05:47:01 UTC.
- Replaces the 30-minute idle and eight-hour absolute limits with a rolling
  365-day HttpOnly cookie/server session, renewed when the app opens. Existing
  valid sessions upgrade on return. Logout/password reset/revocation still apply.
- Browser restarts and cache-only clearing retain sign-in. Deleting cookies,
  private-profile cleanup or browser privacy restrictions can require sign-in;
  no credential is duplicated in JavaScript storage or recovered by fingerprinting.
- [Candidate CI](https://github.com/lupu-spec/Landwolf/actions/runs/37268825471)
  passed 373 backend, 9 frontend and 32 browser tests, PostgreSQL/21-table restore,
  build/package and security gates. Legacy tests and static preflight passed.
- [Live release checks](https://github.com/lupu-spec/Landwolf/actions/runs/37269249419)
  passed exact version/commit/health, four customer journeys and actual Chromium/
  WebKit profile restart, cache-clear and logout persistence checks.
- Payment gates, owner-only coverage, accounts, schema and infrastructure retained.
  Staging was not redeployed. See [commands, evidence and limits](beta/docs/PERSISTENT_SIGN_IN_RELEASE.md).

## v0.9.0 — CRM owner administration candidate, not deployed

- Local implementation `cbbdca8509024c633516be6e616ecad1615d695f` adds contact
  creation/editing, account administration, trial reservations, access grants,
  session revocation and recovery-mail controls; schema 11 is additive.
- Local gates passed 443 backend, 15 frontend and 53 legacy tests, builds,
  packaging, formatting, lint, types and security. Browser launch/download failed
  locally; hosted browser and disposable PostgreSQL/restore gates remain pending.
- GitHub publication was blocked by automatic approval review pending explicit
  approval. No staging or production deployment occurred. Current environment
  records above remain unchanged. See [commands and limitations](beta/docs/CRM_ACCOUNT_ADMIN_RELEASE.md).

### v0.9.0 candidate extension — customer account help, not deployed

Romulus and Remus now offer explicit password-reset requests and customer CRM
profile review/save forms. Email token verification remains required for password
resets. No deletion route or customer access to owner CRM controls is added.
Local gates passed 468 backend, 16 frontend and 53 legacy tests, build/package and
security. Browser launch failed locally; hosted browser/PostgreSQL/restore and
live checks remain pending. Publication is still awaiting explicit approval; no
environment row or deployment changed. See [verification](beta/docs/WOLF_ACCOUNT_HELP_RELEASE.md).

## Source maintenance — October 10, 2026

Production v0.12.0 remained at `7b06ded06beca5bb4b54f3dcbaf83158e072c74f`
during this source check. Seven listing feeds were ready with 272 raw snapshot
records; only the failed Arkansas COSL connection was manually retried. Its
official catalog returned HTTP 500, retaining two last-good records and the
October 9 success timestamp. All five public research adapters worked from
production at the applicable Dallas/Raleigh sample points. Local FEMA HTTP 502
responses did not establish a production outage. No URL/parser change was
confirmed and no source repair was deployed. Billing, access, accounts, allowlists
and quarantine protections were preserved. See
[source check evidence and limits](beta/docs/SOURCE_MAINTENANCE_2026_10_10.md).
