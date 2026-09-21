# LandWolf release log

This is the deployment ledger. A branch head is not proof of a live deployment.
Check each site's `/api/version` for the running version and immutable commit.

## Current environments

| Environment | Site | Observed release | Runtime commit | Last deployment (UTC) |
| --- | --- | --- | --- | --- |
| Production | [landwolf.ai](https://landwolf.ai/) (`www` redirects here) | v0.3.1 | `f96208d897dc22c48f685237eb9477ba1c0b9aa8` | 2026-09-21 15:05:01 |
| Beta | [Isolated beta](https://landwolf-premium-staging.onrender.com/) | v0.3.1 | `f96208d897dc22c48f685237eb9477ba1c0b9aa8` | 2026-09-21 15:00:38 |

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
