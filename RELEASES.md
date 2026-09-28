# LandWolf release log

This is the deployment ledger. A branch head is not proof of a live deployment.
Check each site's `/api/version` for the running version and immutable commit.

## Current environments

| Environment | Site | Observed release | Runtime commit | Last deployment (UTC) |
| --- | --- | --- | --- | --- |
| Production | [landwolf.ai](https://landwolf.ai/) (`www` redirects here) | v0.3.3 | `c5a5c6d6350441fadafc2c4625c3c7d279d0c6a4` | 2026-09-27 22:43:03 |
| Beta | [Isolated beta](https://landwolf-premium-staging.onrender.com/) | v0.4.0-beta.1 | `57663a20bd148525bd5515ce28c027e90751791a` | 2026-09-28 04:41:23 |

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
