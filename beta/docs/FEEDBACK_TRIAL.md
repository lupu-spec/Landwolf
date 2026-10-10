# Conditional self-service feedback trial — v0.11.1 candidate

This candidate adds a separate, explicitly consented offer for new self-service
accounts. It does not change accepted non-charging pilots or CRM grants. The
feature remains off until `LANDWOLF_FEEDBACK_TRIAL_LAUNCH_AT` is set to a deployment
cutoff (Unix seconds), live billing is enabled, and transactional mail is configured.
Only accounts created at/after that cutoff may enroll. Existing Stripe customer
records, pilot enrollment/invite history, owner access and all CRM grant history
exclude automatic enrollment/conversion. Signup alone never authorizes payment.

## Customer terms

Verify email, accept a separate unchecked billing agreement, then use Stripe
Checkout Setup to save a payment method. No charge starts the trial. Feedback is
due 30/60/90 days after verified setup; each form opens seven days early. Every
complete response counts regardless of sentiment or use. A missed check-in
requires a successfully accepted mail notice and at least seven days plus one
hour before the stated $29 USD monthly conversion date. Feedback or online
cancellation prevents conversion. No back-billing or penalty. All three completed
check-ins end the 90-day trial with no automatic charge; paid enrollment is separate.
Trial access ends after 90 days, even if the last notice grace period runs longer.

Consent text/version/time, actual feedback and exact notices are retained in three
additive schema-12 tables. Legacy accepted pilot terms and Stripe price IDs remain
unchanged. Customer UI, signup copy, help agents, CRM counts and public
`/trial-terms` reflect the distinction. Cancellation is online without contacting
sales, with paid renewal cancellation through the existing Stripe portal.

## Financial controls

- Hourly bounded worker, account-row locking, durable conversion intent and Stripe
  idempotency keys. No client timestamp or Checkout redirect can grant access.
- Setup Checkout verifies live mode, customer ownership and a succeeded SetupIntent.
  `managed_payments[enabled]=false` applies only to this setup session: the account's
  default Managed Payments mode does not support setup. Existing paid Checkout and
  the account-wide setting are unchanged.
- Conversion creates a `default_incomplete` subscription without attempting payment.
  The first invoice must match the customer, subscription, monthly price, USD and
  exactly 2,900 cents with one line. Only then set `LANDWOLF* TRIAL OVER` and explicitly
  request payment. Subsequent renewals use existing Stripe Billing.
- A failed notice, unexpected invoice, long outage or unresolved idempotency window
  holds conversion. Never replay a create/payment beyond the bounded window.
- Cancellation is recorded before Stripe reconciliation. An incomplete subscription
  is cancelled without charging; any already active trial subscription stops renewal.
  Existing unrelated subscriptions are never cancelled.
- Confirmation, advance reminders, missed-feedback notices, cancellation and annual
  renewal reminders use the configured support sender. Failed notice delivery
  withholds conversion; five bounded retries are retained for diagnosis.

## Live non-charging API checks (2026-10-10)

Account `acct_1UF0VUPhxY7l1SSN`; existing monthly price
`price_1UF0wdPhxY7l1SSNacgAt3xi` ($29 USD/month). A synthetic verification customer
with no email or payment method was labeled `account_category=smoke_test`.
Setup Checkout creation succeeded only after per-session Managed Payments opt-out.
An incomplete subscription produced a $29 invoice with zero payment attempts.
Setting its first-charge statement descriptor succeeded. It was then cancelled;
the invoice is void with `amount_paid=0` and `attempt_count=0`. No real customer or
card was used. The unused setup session expires automatically; no card was entered.
The connector exposes the preview API, while runtime preserves pinned
`2026-08-26.dahlia`. Payment success/3DS are covered with synthetic contract tests;
no real charge or full card-entry/settlement test has been performed.

An attempted deprecated `pending_invoice_items_behavior` parameter was rejected
before object creation and removed. The explicit invoice validation also prevents
unrelated invoice amounts being charged. Initial migration regression expected
schema 11; updated to schema 12 while retaining all original account-data checks.

## Release status

Candidate, not yet deployed. Production enablement is pending required gates,
isolated PostgreSQL/restore proof, staging and exact release observation. See
`VERIFICATION.md` for results. Tax registrations/settings are unchanged. The terms
implement clear disclosure, consent, reminders and online cancellation; they are
not an attorney's legal opinion for every jurisdiction.

Official references reviewed: Stripe trial compliance and invoice/subscription API
documentation; FTC negative-option/ROSCA guidance; California Attorney General
2025 automatic-renewal guidance. The vacated 2024 FTC rule is not treated as current.


v0.11.0 candidate `bae62d8bc7c152571c8dff3a31b401d2659dda0f` passed all hosted
536 backend / 16 frontend / 96 browser / 53 legacy tests and 32-table restore.
Staging deployment `dep-db4thcvlk1mc73fvrngg` became live 2026-10-10 06:19:36 UTC;
hosted release run 38030474505 passed. It was not promoted. v0.11.1 adds a narrow
UI precedence fix: a later owner invitation/legacy pilot form takes precedence
over historical self-service trial cards. The six responsive trial journeys now
verify that transition explicitly. The live Stripe product display name is
LandWolf Membership; existing prices and cancellation configuration are unchanged.
