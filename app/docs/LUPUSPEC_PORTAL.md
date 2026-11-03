# LupuSpec customer portal — v0.19.0 candidate

Status: **feature branch only; not deployed**. LupuSpec is operated by L91 LLC.
The temporary customer portal uses the existing LandWolf domain at /lupuspec.
There are no LupuSpec taglines or slogans.

## Capabilities

| Capability | Purpose |
| --- | --- |
| Studio | Concept development, CAD, engineering requirements |
| Software | Web, Linux, Windows, macOS and AI applications |
| Fabrication | 3D printing, CNC, custom parts and prototypes |
| Supply | Parts procurement, bills of materials and suppliers |

The customer selects a primary capability and describes any connected requirements.
The public form accepts title, description, optional HTTPS reference link, quantity,
name, email, company and phone. It requires permission to contact the submitter
about the project. It does not request payment and does not subscribe the customer
to marketing. HTTPS reference links are stored, not fetched by the server.
File uploads and automated manufacturing dispatch are not yet enabled.

## Shared CRM

The schema migration seeds the independent LupuSpec CRM project in the L91 CRM
database. All requests create or reuse LupuSpec project-scoped contacts. LandWolf
subscriptions and customer entitlements are not granted or changed.

The owner CRM workspace displays the project request queue, a link to the
associated CRM contact and controls to update workflow status with an optimistic
revision guard and an audit event. A status update is not authorization to spend,
quote, charge, dispatch production work or represent the job as complete.

The customer submission API requires a verified same-origin Origin/Host pair,
bounded body, validated fields, consent and IP/email rate limits. An idempotent
submission UUID protects retries from duplicate requests.

## Shared finances

An owner-only cash ledger records LupuSpec receipts and expenses by Studio,
Software, Fabrication or Supply. This is separate from LandWolf expenses and
Stripe snapshot data. The same Finances dashboard shows the LandWolf totals,
LupuSpec capability totals and an L91 consolidated summary and chart.

LupuSpec entries are owner-entered, not auto-imported or audited bank activity.
The ledger does not perform invoices, payment capture or vendor purchases.
Corrections are signed offset entries that preserve originals. Recording a payment
already reflected by the same Stripe account again in LupuSpec is double counting:
the owner must reconcile overlapping sources before relying on consolidated totals.
Consolidated receipts and net are unknown when LandWolf Stripe has not been verified.

## Data boundaries, release and next integration

The additive schema 14 tables are lw2_lupuspec_requests,
lw2_lupuspec_request_events and lw2_lupuspec_finance_entries. Existing LandWolf
accounts, billing, trials, CRM projects, finance transactions and listings remain.

New owner endpoints:
- GET /api/admin/lupuspec/requests
- PATCH /api/admin/lupuspec/requests/{request_id}
- POST /api/admin/finance/lupuspec/entries

Existing shared endpoints:
- GET /api/admin/finance
- GET /api/admin/crm/contacts?project_id=lupuspec

**Not implemented:** automated dispatch into the independent L91 Software Factory;
purchase orders; external fabrication-provider APIs; CAD file uploading; quoting,
invoicing, charging cards or customer-facing job tracking. These require a separately
tested approval and supplier integration before work may be dispatched.

Production requires the repository's standard predeploy schema migration, all
mandatory verification gates, an observed Render release and an immutable release
ledger entry. Branch commits are not a production deployment.
