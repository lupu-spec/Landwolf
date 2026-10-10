# CRM account categories and user statistics

Candidate v0.10.1. Deployment evidence will be recorded after live verification.

Open **L91 LLC CRM** to see Users, Trial users and Paid users. Click any count to
show the matching accounts. **Account category** separates Users, Owners, Smoke
tests, and unregistered/external-project contacts. The default **People (hide
smoke tests)** keeps real contacts and the owner visible. Select **User** for
registered LandWolf accounts that are neither the owner nor a recognized test.
Use **Membership** to filter trial/paid status, and **Export contacts CSV** to
download that exact filtered list with category, membership and billing-sync time.

Smoke tests are retained in their own category, excluded from default lists and
exports, and never included in user/trial/paid statistics. Select **Smoke test**
or **All records, including smoke tests** to inspect them. No accounts are deleted,
suspended, granted access, or billed by classification. Categories are recomputed
from existing facts on every read, so existing and future test accounts are handled
automatically without a recurring job or new service.

## Counting rules

| Category | Rule |
| --- | --- |
| Owner | The configured immutable owner account ID; takes precedence over test detection |
| Smoke test | LandWolf contacts matching the known test identities below |
| User | A linked, email-matched LandWolf account that is neither owner nor smoke test |
| Contact / external project | Unregistered contacts and contacts managed by another project |
| Paid user | Stored Stripe subscription status is active and paid-through time is in the future |
| Trial user | Current owner trial grant, accepted unexpired feedback pilot (including feedback overdue), or stored Stripe trialing status |
| Complimentary | A current owner grant that is not a matching current trial reservation |
| Trial invited / reserved | A trial reservation, unaccepted pilot invitation, or not-yet-claimed configured pilot reservation |
| Trial ended | A previous trial/pilot without current paid, trial or complimentary status |
| Billing needs attention | Stored past-due, unpaid, incomplete or paused Stripe status without another current access category |
| Registered, no active plan | Other registered users, including a subscription without current paid-through coverage |

Paid takes precedence over trial, so a customer with both is counted once as paid.
The membership categories sum to Users. Suspended subscribers still count according
to their billing record: suspension does not cancel their subscription. Counts are
not revenue, an invoice ledger, a historical conversion metric or proof of payment.
Reporting does not call Stripe or activate reservations. The view shows the report
time and warns if billing records are over 24 hours old. Normal webhooks and the
existing billing refresh continue to update the stored facts.

Counts follow project, search, stage, industry and primary-use filters, before
account-category and membership filtering. Owners and tests are always excluded
from Users, Trial users and Paid users. Unregistered contacts are not trial users
merely because access has been reserved for them.

## Conservative automatic test detection

The recognized prefixes are `production-smoke-`, `staging-smoke-`, `smoke-`,
`hunt-save-qa-`, `hunt-browser-qa-`, `deployment-check-`,
`national-deployment-check-`, `free-api-check-`, `domain-check-`, `qa-saved-`,
`qa-navigation-` and `qa-retirement-`, only on reserved `example.com` or
`example.invalid` addresses. The older patterns were confirmed in a read-only
production audit (12 legacy verification accounts). The exact support Gmail plus alias used for the
October 10 recovery verification is also recognized. A real email address or
name containing “test,” “smoke” or “QA” is not enough. Detection is limited to the
LandWolf project; other projects retain their own account meaning. A previously
unknown testing convention needs a reviewed rule rather than a broad name match.

## Owner and operational interfaces

- `GET /api/admin/crm/contacts` and `.csv`: `account_category=people` by default;
  supported alternatives `all`, `user`, `owner`, `smoke_test`, `contact`.
- `membership=paid` or `trial` selects matching users; additional keys are listed
  in the project's categories response. Invalid values return 422.
- `GET /api/admin/crm/statistics`: aggregate counts for all CRM records.
- `python -m landwolf.cli crm-summary`: aggregate-only read-only operational job.
  Run in the existing service environment. It prints no emails or credentials,
  performs no schema bootstrap or external requests, and changes no records.

All HTTP reporting endpoints retain server-side owner authorization. Test status
is a reporting label, never an authentication role or entitlement. Filtering happens
before pagination and CSV limits. The 10,000-row CSV bound and formula escaping
are preserved. Private counters and records are cleared at sign-out or lost owner
authorization. There is no schema migration, dependency change or billing change.
