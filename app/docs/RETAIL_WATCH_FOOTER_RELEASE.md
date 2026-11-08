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

ACT: all declared internal gates passed without an application repair. PR #56
merged as 2562941200eff7ea3944480d89ca09b844218501. Staging deployed
d375ee9346320d9890d31aeb27456db67b437984 via dep-dbo06uff3r2c739qpup0,
live 2026-11-08 05:08:13 UTC. Production deployed via dep-dbo07tqjnfac73difshg,
live 05:09:59 UTC. Candidate, staging and production share the complete tree
87a855e101b63ff9fdfe672e4065461f6a90debb. Read-only checks finished at
05:08:43 UTC in staging and 05:11:04 UTC in production: exact version/commit,
health, environment/billing mode, unique correct footer targets and new-tab
protections passed. The www HTTPS identity and supplied branding assets also passed.
No warning/error appeared in the sampled post-release app-log windows recorded
in deployments.json. This is a bounded log sample, not a claim about all traffic.

## Executed checks

All commands below passed on the final candidate; exact timestamps and outcomes
are retained in local-checks.json, ci-evidence.json and the CI summary files.
Commands use the app environment unless another directory is stated.

- `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check`.
- `.venv/bin/ruff check landwolf tests scripts`; `npm run lint`.
- `.venv/bin/mypy landwolf`; `npm run typecheck`.
- `npm run test:unit`: 28 passed; `.venv/bin/pytest -q -m 'not browser'`: 784 passed.
- `.venv/bin/pytest -q tests/test_public_pages.py`: 24 passed in this cloud checkout.
- `.venv/bin/python scripts/check_postgres.py`; `scripts/check_restore.py`:
  disposable PostgreSQL integration and exact restored row digests across 49 tables.
- `npm run build`; early four mobile accessibility journeys; existing commercial,
  public-page, theme, source-list, mobile-research, dock and assistant browser groups;
  `.venv/bin/pytest -q -m browser`: 172 passed. Focused cases overlap the full suite.
- Independent header job: two exact cascade/screenshot cases passed.
- `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py`.
- `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable`;
  `npm audit --audit-level=moderate`; `npm run secrets`.
- `git diff --check`; `git status --short`.
- Factory bridge CI: `npm ci`, `npm run typecheck`, `npm test` (36 passed),
  `npm audit --audit-level=moderate`, in integrations/l91-factory-api.
- Isolated legacy CI: requirements installation and `PYTHONPATH=. pytest -q`:
  53 passed. Application, factory and legacy runs are 42446911747, 42446911790,
  and 42446911677 respectively.
- The recorded `verify_live.py` ran from the repository root against both
  deployed origins with their exact commits; both commands exited 0.

## Performance and limits

The complete application job took 2229 seconds (37m 09s); its full browser suite
reported 1567.31 seconds. Factory bridge and legacy jobs took 13 and 35 seconds.
Deployment intervals were 68.011 and 48.073 seconds; separate image-build timing
was not captured. These are observed execution durations, not model benchmarks.

CI fixture screenshots at 390px and 1440px were visually inspected and show both
footer links fitting. CI also exercised Chromium/WebKit at 390/834/1440 widths.
Live checks verified returned markup, HTTPS and service identity, not computed
live-browser layout or a physical device. Browser archive installation failed in
this cloud session; setup errors and the headless fallback's measured attempt are
retained. No local-model inference ran, so model/hardware/token/throughput/cost
metrics remain unknown. The audit helper initially had lint/line-length issues;
formatting corrected them and its final lint check passed. See checker-quality.txt.

Separate durable records are factory-runs/retail-watch-footer-20261108/
`factory-performance.json` and `local-ai.json`. The same directory retains PDCA
transitions, source/CI/artifact hashes, failed setup/control attempts, actual check
outputs, deploy records and live proofs. GitHub screenshot artifacts expire on
2026-11-15; textual outcomes and hashes remain in the repository. Retail Watch
sharing, collectors, experiment records and publication were not changed. The
previous 0.24.1 image is schema-compatible; no database change or restore occurred.

Factory improvement observation: expose a read-only runner/model health receipt
through the authorized connector so future cloud jobs can distinguish offline
hardware from unavailable control access without guessing or probing local ports.
