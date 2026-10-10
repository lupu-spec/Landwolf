# Billing deployment and activation status — 2026-10-05 UTC

## Observed production state

Version `0.4.0`, commit `7af4d957d621023060eef16b4c1afcfa057ec111`, is deployed on the existing production service `srv-dak1lvh42hec73blur00`. The public HTTPS responses were independently observed after the recovery deployment:

- `/api/health`: `{"status":"ok","version":"0.4.0","payments_enabled":false}`.
- `/api/version`: version `0.4.0`, environment `production`, commit as above.
- `/api/session`: unauthenticated, payments disabled, email delivery disabled.

**The live paywall is NOT activated. No charge or subscription was created during this attempt.**

## Deployment ledger supplement

| UTC | Environment | Commit | Render deployment | Observed result |
| --- | --- | --- | --- | --- |
| 2026-10-05 01:08:08 | Staging | `3b53b6d8aff9b2715bbe0c45f1ec71848ebc1b8f` | `dep-db1fgfgu01pc73e766ig` | Live; exact HTTPS version/health, signup, navigation, Explore, Hunt, Membership with payments disabled, and sign-out observed. |
| 2026-10-05 01:15:56 | Production | `7af4d957d621023060eef16b4c1afcfa057ec111` | `dep-db1fk3ou01pc73e7lu80` | Live with payments disabled. Schema v8 initialization and application startup completed. |
| 2026-10-05 01:16:46 | Production activation attempt | same | `dep-db1fkqegekts73djtf1g` | FAILED during pre-deploy Settings validation; never became live. |
| 2026-10-05 01:18:56 | Production configuration recovery | same | `dep-db1flns9v7es73fbeelg` | Live with payments disabled. Public version, health and session responses confirmed afterward. |

PR #12 was merged after the normal release gates and staging checks. GitHub comparison confirmed that the merge commit has no file differences from the tested candidate. Auto-deploy remains off. Production secrets were never read, logged, published, or replaced by this work. Only non-secret plan/account/portal settings and the payment flag were updated through merge-only Render actions. Existing owner settings and private pilot reservations were not overwritten.

## First activation blocker

Pre-deploy ran `python -m landwolf.cli init-db` and exited 1 before migration or Stripe authentication during the activation attempt. Its exact validation message was:

> Payments require a live Stripe server key; sandbox is forbidden

This is a local format check, not a Stripe API rejection. It means `LANDWOLF_STRIPE_SECRET_KEY` was absent or failed the supported live-key prefix/minimum-length condition. Possible causes include the wrong variable name, a test or publishable key, leading quotation marks/whitespace, or a truncated value. The secret value was not retrieved, so the exact cause is not yet known. The webhook and owner/account/price startup checks occur later and are not verified by this failed attempt.

The owner must correct the exact prefixed variable in the existing production service's Environment page, using the complete live server key privately. Keep payments disabled while saving. The unprefixed legacy `STRIPE_SECRET_KEY` is not an implicit fallback. Do not weaken this validation or put a key in source, chat, logs, or artifacts.

## Verification and limitations

- **Passed:** Normal beta PR gate `37246215775`, job `111564537570`: formatting, lint, Python/TypeScript types, unit/API tests, PostgreSQL integration, disposable restore, browser journeys, package, security and diff integrity. Command list is retained in `LIVE_BILLING_VERIFICATION.md`. No runtime code changed in this continuation.
- **Passed:** Root test run `37246215575` and static preflight tests `37246215535`, previously observed for the same candidate. Runtime preflight jobs skipped in that workflow are not counted as passed.
- **Passed:** Isolated staging browser flow and exact runtime identity. Its observed six navigation labels matched the repository. A separately requested Analyze navigation item was an incorrect test expectation; analysis is inside property detail, not a top-level tab. The ad hoc staging run did not establish a complete multi-viewport matrix; CI provides that coverage.
- **Passed:** Additive schema v8 production initialization, preserved existing production service/database and application startup. No production restore was performed. The database is an available paid basic_256mb Render Postgres instance; Render documents automatic point-in-time recovery on paid instances. An individual recovery/export snapshot was not inspected.
- **Failed:** Live activation key-format validation, as above.
- **Not run:** Live Checkout, real purchase lifecycle, signed live webhook delivery, and authenticated owner/pilot runtime checks. A browser request for live checkout testing was blocked by a safety check and was not executed or retried through another route. The later public health check used GET only.
- **Separate observed issues:** IRS source refresh reported changed field layout; Minnesota DOT refresh reported changed sale identifier/document URL. Those source adapters were not changed during this billing task. Email delivery remains disabled; reserved pilot identity confirmation/enrollment therefore still uses the owner-assisted route documented in `LIVE_BILLING.md`.

Old v7 images are incompatible with schema v8. Keep the current v8-compatible code for recovery; do not roll back to a v7 image or reset account data. This documentation-only commit does not constitute another runtime deployment.
