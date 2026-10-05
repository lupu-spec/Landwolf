# L91 LLC CRM

L91 LLC CRM is the private customer workspace for L91 LLC projects. Open the
**L91 CRM** dock icon after signing in as the configured LandWolf owner. The page
heading and accessible navigation label use the full **L91 LLC CRM** name.

## Registration and contact categories

| Category | Fields / recommended values |
| --- | --- |
| Identity | Full name (required), existing account email (required), phone (optional) |
| Company | Company, job title, industry (optional) |
| Contact role | Investor, agent/broker, developer/builder, lender, business owner, individual, other |
| Intended use | Investing, property research, deal analysis, client work, development, personal land purchase, exploring, other; optional free-text goals |
| Industry | Real estate; construction/trades; woodworking/manufacturing; technology/AI; finance/lending; professional services; personal use; other |
| Lifecycle | Registered → qualified → contacted → customer; inactive when appropriate |
| Follow-up | Date, tags, private notes, dated activity |
| Project and origin | Connected project, source, external user ID, registration and update timestamps |
| Communication permission | Explicit email marketing choice, wording version, recorded time; no assumed SMS/call consent |

The registration form requires full name and primary use. Company, phone, job
title, industry, role, goals and email marketing are optional. A missing required
profile returns HTTP 422 for API registrations too; existing login contracts stay
unchanged. Old cached signup pages must reload after this release. Existing users
can still sign in without completing a new form. Existing records contain only
known email/registration details and are marked `existing_account`; names,
companies, phone numbers and permission are never inferred.

Account creation and CRM capture share one database transaction. A failed capture
cannot leave a successfully registered account without its contact. Passwords,
sessions, billing credentials and recovery tokens never enter the CRM.

Lifecycle is an owner's relationship category, not a subscription entitlement or
automatic assertion of payment. This version does not send marketing, start
sequences, charge customers, synchronize billing stages, enrich profiles, or read
private property research. Permission is project-specific. No opt-in authorizes
marketing for a different L91 project.

## Use the workspace

1. Open **L91 CRM** as the owner. Filter by project, industry, use, stage, or a name,
   company or email search. Lists use 50 records per page.
2. Open a contact to review their profile, update lifecycle/tags/follow-up date,
   add a note, or record an email unsubscribe. Concurrent stale edits return 409
   instead of overwriting another update. The latest 100 activities are shown.
3. **Export contacts CSV** downloads the current filtered result set, across all
   pages. Exports cap at 10,000 rows and reject larger results without truncating.
   Spreadsheet formula prefixes are escaped. The browser controls the device's
   download location; on iPhone/iPad this follows Safari/Files settings.
4. Open **Connect another project** to create an isolated project and obtain its
   write-only connector key. Store it in the other project's server secrets.
   Keys are displayed only once; rotate or revoke them from the same panel.

Only the immutable owner account configured by `LANDWOLF_OWNER_ACCOUNT_ID` has
CRM access. LandWolf currently has no separate administrator role. Customer
accounts and connector keys cannot read any contact list, notes or CSV. Ordinary
user screens never request the CRM. Signing out, changing screens, or receiving
a CRM authorization denial erases loaded CRM data. No CRM content or key is
stored in localStorage/sessionStorage. Data resides in the existing managed
PostgreSQL database; backups and host access remain part of normal operations.

## Connect a future project

Create a project (for example `woodworking`) in the CRM. From that project's
backend, after its successful registration, call:

```http
POST https://landwolf.ai/api/crm/v1/projects/woodworking/registrations
Authorization: Bearer <project key from server secrets>
Content-Type: application/json
```

```json
{
  "external_id": "immutable-user-id-in-your-project",
  "email": "person@example.com",
  "full_name": "Example Person",
  "company": "Example Company",
  "phone": "+1 555 010 1234",
  "job_title": "Owner",
  "industry": "woodworking",
  "contact_type": "business_owner",
  "primary_use": "project_management",
  "use_details": "Track custom orders",
  "marketing_opt_in": false
}
```

The minimal payload requires `external_id`, `email`, `full_name`, and `primary_use`.
External category codes are extensible (`a-z`, `0-9`, `_`, maximum 40 characters).
For true email permission, supply `consent_version` identifying the exact wording
shown by that project; the source project must retain that wording and evidence.
The receiver records receipt time, not an asserted historical consent time.
Unknown fields are rejected. Phone allows 7–15 digits with spaces, punctuation,
and an optional leading country code. It is not a phone ownership verification.

Successful creation or repeat returns `{ "contact_id": "…", "status": "captured" }`.
A retry with the same project, external ID and normalized email returns the same
contact without overwriting it. Reusing an identity with another email, or another
identity with an existing email in that project, returns 409 for human resolution.
Different projects can retain separate contacts with the same email. There is no
cross-project automatic merge and no connector read API.

Use HTTPS and a backend outbox: persist the registration event locally, send it
with a 10-second HTTP timeout, and mark it delivered after HTTP 200. Retry 429/503
with bounded exponential backoff and respect Retry-After. Keep permanent
401/409/422 failures visible for an operator; retrying an unchanged invalid event
will not fix it. Protect outbox payloads as contact data. Registration ingestion
is bounded to 120 requests/minute per project and per source IP, and a 16 KiB
request body. No browser Origin is accepted, and no cross-origin browser API is
exposed. Never put a connector key in browser JavaScript, a URL, source control,
or a log. Rotation immediately invalidates the previous key.

## Portability, migration and operations

`landwolf/crm_core.py` is the portable storage/validation module. It depends on
SQLAlchemy and Pydantic/email-validator, with no LandWolf authentication, billing,
UI or networking dependency. Another Python application can copy/import it,
create `CRMBase.metadata`, provision projects, and call `capture(session, ... )`
inside its transaction. `landwolf/crm.py` supplies the LandWolf auth/API adapter;
`web/crm.ts` supplies the owner interface. The versioned HTTPS intake API is the
preferred bolt-on for projects using any language.

Schema 10 adds `crm_projects`, `crm_contacts`, and `crm_activities`. The existing
migration transaction/lock creates the tables, seeds the LandWolf project and
backfills only existing account facts. Unique project+email and project+external
ID constraints prevent duplicate identities. Re-running initialization is safe.
Existing account, billing, pilot and research records are preserved.

No infrastructure, paid service, runtime dependency, or external CRM vendor is
added. Deploy through the existing staging-first process after gates. The old
v0.7 app rejects schema 10; use a schema-10 compatible fix-forward rollback. Do not
drop CRM tables or reset the schema version in production. Restore rehearsals
use only the disposable CI PostgreSQL database; hosted backup restoration is a
separate operational procedure.

Scope: contact capture/segmentation/follow-up workspace and project intake, not a
full sales ERP. Profile correction/deletion requests currently require an owner
operational data update; the UI edits lifecycle, tags, follow-up and notes. No
external project is connected until its backend implements the intake call.

Standard contact fields were cross-checked against HubSpot's published contact
property reference: https://knowledge.hubspot.com/properties/hubspots-default-contact-properties
