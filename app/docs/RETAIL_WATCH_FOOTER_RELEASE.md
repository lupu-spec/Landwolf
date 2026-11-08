# Retail Watch footer — PDCA work order

PLAN: after Audit Desk PR #55 and its production deployment finished, add exactly
one Retail Watch footer link, preserving Audit Desk, all public navigation and
private app access. Runtime version 0.24.2; no schema or dependency changes.

Prerequisite observed 2026-11-08 UTC: PR #55 merged at 04:02:33; production
dep-dbnv8ojrjlhs739vt6c0 went live at 04:03:40. Live /api/version returned
0.24.1 and 9c8d08b229d343ff821e06b3cba322c1fb5e7398. The live footer contained
the exact private Audit Desk URL. Main's release ledger records completed
staging/production verification. The separate conversation's search index was
older than this direct deployment/release evidence. Source begins at
9a5526662edd2b8bdba48c6a321bfdec37d5dad7.

DO: add the plain Retail Watch URL confirmed by Sites get_site, opening in a new
tab with noopener/noreferrer. Preserve owner-only Site access and existing links.
Add HTTP uniqueness/label/target checks and responsive browser checks. Version
metadata changes together; dependency resolutions remain unchanged.

CHECK: use the actual L91 PDCA controller from factory revision
d5352b028f2881a6c85ec5f8b82596be4ba9e8f1. Its default main branch is the older
generator. Hosted application, Factory bridge and legacy CI remain required;
staging must be observed before production. Source-bound logs and audits are
retained under factory-runs/retail-watch-footer-20261108. ACT means declared
internal checks passed, not independent human review or model certification.

Local AI: owner authorization supersedes the older OFF policy for this work,
but no registered model endpoint is exposed to this cloud execution host.
The existing documented runner uses outbound polling through the owner portal.
The connected-browser bootstrap returned `Unknown tool browser.js`; no model
request or local runtime execution occurred. Factory Git clone also failed with
missing GitHub shell authentication; the connected GitHub API supplied the pinned
PDCA source. Fallback is cloud-authored implementation and independent executable
CI. Actual model, hardware, token count, throughput and model cost are unknown.
No local model configuration, credentials, ports or paid service was changed.

ACT: pending current checks and observed staging/production deployment. Preserve
failed attempts and append actual outcomes; do not call a candidate deployed.

Factory improvement observation: expose a read-only runner/model health receipt
through the authorized connector so future cloud jobs can distinguish offline
hardware from unavailable control access without guessing or probing local ports.
