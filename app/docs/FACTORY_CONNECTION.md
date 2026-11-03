# Customer requests and local factory

Owners open CRM → CUSTOMER WORKSPACE, set Software work to APPROVED, then open
FACTORY RUN. Review the exact submitted requirements, choose a registered project
and runtime, add acceptance requirements, check the approval box and choose RUN REQUEST.
REFRESH RUN loads status and the returned report/patch. CANCEL RUN stops queued work
or stops active work at its next heartbeat. Results are owner-only; publish a separate
customer update when ready. The local machine must be awake with Ollama, Docker and
l91-runner.service running. Offline requests remain queued.

Only Software work can run. New projects receive syntax/compile checks, not functional
acceptance. Registered projects retain their independent tests. Nothing applies,
merges or deploys generated code. A work item has one factory task; use OPEN FACTORY
for subsequent code-review iterations or reruns of that same task.

## Access boundary

The browser calls existing same-origin owner APIs with a session and CSRF token.
Customers cannot list targets, dispatch, read results or cancel. The server resolves
project requirements from its database; browser-supplied prompts, customer IDs, host
paths, machine IDs and shell commands are rejected. Only title, requirements,
acceptance criteria and selected target/runtime are forwarded; CRM contact metadata,
financial records and internal notes are excluded.

LANDWOLF_FACTORY_TOKEN is a private 64-character server credential, scoped in the
factory database to a single existing owner and runner. Its SHA-256 hash is stored
in portal_connections; the factory never returns the token. Bridge endpoints reject
Origin headers and do not expose CORS. Rotating the connection token or revoking the
connection blocks further portal access. Revoking the runner also blocks the bridge.
The portal uses a fixed HTTPS API origin, bounded timeouts/responses and no redirects.

Factory code and migrations are versioned in integrations/l91-factory-api. The existing
Clerk website and machine credential endpoints remain separate. The machine keeps its
outbound-only polling connection and existing isolated, network-disabled Docker checks.
No local port, customer access to the runner or automatic customer-triggered execution
is introduced.

## Delivery and recovery

Schema 16 adds lw2_factory_dispatches, with one row per Software work item, owner
approval, work revision and frozen payload. The transaction commits before network I/O.
A timeout leaves a pending durable request. Refresh first; RETRY SAME REQUEST reuses
the same ID and payload. Different payloads/revisions are rejected after approval.
Cloudflare migration 0005 adds scoped connections and dispatch mapping. Mapping,
task, queued run and event are created in one D1 batch; replay does not create more
work. Queue limits and registered target checks remain enforced. A runner lease prevents
concurrent machine jobs; cancellation rejects late uploads.

A pending local record means delivery is unknown, not proof that no job ran. Refresh
or retry the same request; never create a duplicate project to recover a timeout.
Unavailable credentials preserve the record and fail closed. Status is explicitly
refreshed, not continuously polled. Result claims are shown as reported by the runner.

## Deployment

Run the portal's full gates and the factory API's npm ci, typecheck, tests and audit.
Apply additive D1 migration 0005 before the updated Worker. Provision an integration
row using the existing paired owner/runner and a random token hash. Store the token
only as LANDWOLF_FACTORY_TOKEN in the intended Render service; never in source, frontend,
logs or output archives. Use separate staging and production connection credentials.
Existing pairings, tasks, notes and results remain intact. The portal database migration
runs through the established staging startup/production predeploy commands.

Validate owner approval → durable portal record → factory queue → real local inference
→ sandbox verification → private report. Test cross-account access, ambiguous delivery,
invalid targets, stale revisions, cancellation and revoked connections separately.
Schema 16 requires a forward fix or reconciled database recovery if rolling back to
schema 15; a code-only rollback to an older schema guard cannot start.
