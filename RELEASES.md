# LandWolf release log

This is the deployment ledger. A branch head is not proof of a live deployment.
Check each site's `/api/version` for the running version and immutable commit.

## Current environments

| Environment | Site | Observed release | Runtime commit | Last deployment (UTC) |
| --- | --- | --- | --- | --- |
| Production | [landwolf.ai](https://landwolf.ai/) (`www` redirects here) | v0.4.2 | `3f395b4a546c806d7eacd04229f3ac6a1f510659` | 2026-10-05 04:55:21 |
| Beta | [Isolated beta](https://landwolf-premium-staging.onrender.com/) | v0.4.1 | `cf34432724b9aae2afa32987362a4df67f57eb86` | 2026-10-05 01:45:45 |

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
