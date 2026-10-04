# Live billing activation — v0.4.0 candidate

This document is configuration guidance, not proof of deployment. The production
service remains `landwolf-free-beta` / branch `codex/landwolf-beta-rebuild` / Docker
context `beta`. Keep its existing database and custom domains. Do not deploy the
legacy `main` app or copy legacy account/password/session tables into this app.

## Access contract

All property search, detail, sources, analysis, research, new Hunts, Hunt matches
and Hunt events enforce billing on the server. Sign-in, sign-out, recovery,
verification, feedback, membership and existing saved-Hunt management remain
available without a subscription. Owner identity remains an immutable account ID;
email strings cannot grant owner privileges. Existing audited complimentary grants
remain valid. Removing a grant requires another valid entitlement immediately.

Accepted active pilots retain three calendar months from acceptance, baseline and
scheduled day-14/30/60/85 feedback, existing grace periods, and no automatic charge.
Survey completion cannot extend expiry. A paid subscription can independently
restore access after a pilot expires or its surveys are overdue. Checkout blocks
accounts that already have owner/complimentary/eligible-pilot/paid access.

A private email reservation is not an entitlement or proof of email ownership.
`LANDWOLF_PILOT_INVITE_EMAILS` is a JSON array maintained only in Render, not in
source or frontend assets. Verified matching accounts receive one invitation, not
an active pilot. They must accept the terms and starting survey. Unverified users
are directed to verification or replying to their original invitation. When mail
is not configured, the owner confirms identity from the reply and uses the existing
owner Feedback controls to invite the account. Never mark arbitrary sign-ups
verified just because their email matches a marketing list. Revoked/expired pilot
history cannot be recreated by signing in again. One account per normalized email
is enforced by the existing database constraint.

## Required runtime settings

Set these on the existing production Render service; merge, never replace its
entire environment. Secrets must be entered through a secure dashboard/session,
never chat, source, command output, screenshots, logs, or CI artifacts.

| Name | Required value |
| --- | --- |
| `LANDWOLF_PAYMENTS_ENABLED` | Explicit `true` only at the final activation step. |
| `LANDWOLF_OWNER_ACCOUNT_ID` | Existing confirmed owner account UUID, not an email. |
| `LANDWOLF_STRIPE_SECRET_KEY` | Server-side live key for the intended account; sandbox keys are refused. |
| `LANDWOLF_STRIPE_WEBHOOK_SECRET` | Signing secret for the live `https://landwolf.ai/api/billing/webhook` endpoint. |
| `LANDWOLF_STRIPE_ACCOUNT_ID` | Intended live merchant account ID. |
| `LANDWOLF_STRIPE_MONTHLY_PRICE_ID` | Active live USD $29 recurring monthly price. |
| `LANDWOLF_STRIPE_ANNUAL_PRICE_ID` | Active live USD $299 recurring annual price, not the separate one-time price. |
| `LANDWOLF_STRIPE_PORTAL_CONFIGURATION_ID` | Active live portal with cancellation at period end, invoice history and payment-method updates. |
| `LANDWOLF_PILOT_INVITE_EMAILS` | Private JSON array of exact normalized outreach recipients. |

Do not configure browser publishable keys: hosted Checkout collects payment details
on Stripe. Existing opaque sessions require no legacy JWT `SECRET_KEY`. Runtime
keys are scoped to this rebuilt app and do not reuse a legacy app's unprefixed env
values implicitly. Startup validates the live merchant, prices, owner existence,
and live portal before serving when payments are enabled. Billing uses the pinned
Stripe API version `2026-08-26.dahlia` and subscription-item billing periods.

## Payment lifecycle

The authenticated server selects the price and customer, requires CSRF plus explicit
recurring-payment consent, stores the idempotency attempt before calling Stripe,
and serializes checkouts per account. Repeated/lost requests reuse a checkout;
switching plans expires the prior open session. Existing nonterminal subscriptions
block a second subscription. Card data never reaches LandWolf. Completing a return
URL alone never grants access: the server re-reads Stripe state for the authenticated
account's mapped customer.

Only active automatic-charge subscriptions with the allowed price, quantity one,
matching app/account metadata, and a future period end grant paid access. Trialing,
incomplete, past-due, unpaid, paused and canceled states do not. A scheduled
cancellation retains access through the paid period. There is no background charge
or subscription creation when a pilot expires. Comp grants do not independently
cancel a pre-existing Stripe subscription; manage any such subscription explicitly.

The webhook requires the raw-body SHA-256 HMAC and a five-minute timestamp tolerance,
rejects non-live events, and refreshes authoritative current subscriptions under the
same account lock. Duplicate event receipts and entitlement updates commit together;
delayed events cannot replay old paid state. Unknown customers are ignored, never
matched by email. Payloads/card details are not stored. Relevant events are Checkout
completion/asynchronous outcome, subscription lifecycle, and invoice paid/failed/
action-required. The existing broader webhook can remain enabled; unrelated events
are acknowledged without changes. An invalid signature must return 400, not 200.

Paid entitlements refresh after at most five minutes of use and at an expired
active period boundary. Stripe failure returns 503 rather than inventing access or
silently treating a subscriber as unpaid. Eligible pilots and owner/complimentary
accounts do not depend on a Stripe network call. Customer portal sessions are
restricted to the authenticated account. Portal cancellation is at period end, with
no unrequested plan change or proration. No raw provider errors are returned.

## Migration and rollout gates

1. Run every existing beta/root CI gate, plus the new billing unit/API and browser
   regressions. Run PostgreSQL migration/restore only on disposable CI databases.
2. Confirm a recoverable production backup under the hosting retention policy.
   Schema v8 adds two tables, without dropping or rewriting existing account,
   Hunt or feedback data. Existing permanent Saved-removal behavior is unchanged.
3. Check the exact live prices, merchant capability, portal and webhook configuration.
   Securely provide live secrets and pin the actual owner. Add outreach recipients
   privately. Confirm invited users can be enrolled without a card.
4. Deploy the exact tested candidate to isolated staging before production. Fake
   Stripe fixtures are tests, not proof that real payments work. Never configure
   sandbox keys on production. Do not create real charges as an unattended test.
5. Activate and deploy on the existing production service only after configuration
   is ready. Observe Render deployment status, HTTPS health, version and commit.
6. With an owner-controlled ordinary account, verify unpaid APIs return 402, create
   a live hosted Checkout session displaying the selected price, then expire the
   session without submitting payment. Verify owner and real pilot entitlements.
   A real paid subscription lifecycle is unverified until an explicitly authorized
   purchase and its genuine webhook have been observed. Do not use test cards live.
7. Verify invalid webhook signatures return 400; a signed live delivery must be
   accepted and deduplicated. Check portal cancellation availability. Confirm no
   access was granted merely by visiting a success URL.
8. Record exact results/deploy IDs in the release ledger. A pushed branch, mocked
   Stripe response, enabled merchant account, or created portal is not a deployment.

## Rollback and retained limitations

The schema is version-checked at startup. After v8 migration, use a v8-compatible
fix-forward/rollback build; an old v7 binary will reject the new schema. Roll back
the release/config deliberately, not by deleting billing data or changing schema
numbers. Disabling payments intentionally restores the old free-access behavior;
that is an owner-controlled emergency action, not an automatic failure fallback.
The new two tables have no destructive down migration.

Email delivery is a separate pre-existing setup and is not assumed enabled. Until
verified email delivery is configured, pilot identity confirmation/enrollment is an
owner action following the outreach reply. New recipients are not discovered from
Gmail at runtime: keep the private list or owner invitations current. Sales-tax
settings, legal policies, refunds and real-card lifecycle validation need their own
business-owner review; this change does not invent registrations or make charges.
