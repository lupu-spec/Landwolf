# Billing diagnostics result — 2026-10-05 UTC

## Confirmed production result

The status-only pre-deploy diagnostic at 2026-10-05 01:48:35 UTC reported:

| Process environment variable | Observed status |
| --- | --- |
| LANDWOLF_STRIPE_SECRET_KEY | missing |
| LANDWOLF_STRIPE_WEBHOOK_SECRET | missing |
| STRIPE_SECRET_KEY | missing |
| STRIPE_WEBHOOK_SECRET | missing |
| LANDWOLF_OWNER_ACCOUNT_ID | missing |
| LANDWOLF_STRIPE_ACCOUNT_ID | present |
| LANDWOLF_STRIPE_MONTHLY_PRICE_ID | present |
| LANDWOLF_STRIPE_ANNUAL_PRICE_ID | present |
| LANDWOLF_STRIPE_PORTAL_CONFIGURATION_ID | present |
| LANDWOLF_PILOT_INVITE_EMAILS | present |

These are process-environment observations, not secret values or a dashboard
inventory. The diagnostic found no server-key value to classify as a test,
publishable, or live server key. It does not establish where the owner saved
entries in the dashboard. The required secrets and immutable owner UUID need to
be configured under Environment Variables on `landwolf-free-beta`, service
`srv-dak1lvh42hec73blur00`. Secret Files, another service, or an unlinked environment
group are not equivalent to this service's environment. No automatic fallback to
legacy unprefixed keys was added. No database networking rule was weakened.

## Deployment ledger supplement

| Finished UTC | Environment | Version / commit | Deploy | Result |
| --- | --- | --- | --- | --- |
| 2026-10-05 01:31:42 | Production activation attempt | v0.4.0 / c9c0d9c96e54f63005b9d67b2a2b789abcd1fae3 | dep-db1frqnavr4c73bne27g | Failed before activation: same generic live-server-key validation error. |
| 2026-10-05 01:32:58 | Production recovery | same | dep-db1fsbegekts73dkraqg | Live, billing disabled; public identity/health observed. |
| 2026-10-05 01:45:45 | Staging | v0.4.1 / cf34432724b9aae2afa32987362a4df67f57eb86 | dep-db1g20ou01pc73e9dbi0 | Live; exact HTTPS identity and health confirmed, payments false. |
| 2026-10-05 01:48:50 | Production | v0.4.1 / 0301e31c18f087c1cadebbcd3557f6ddc2973876 | dep-db1g3jtg1s2s73a17kc0 | Live; sanitized configuration result above; fresh HTTPS identity and health confirmed, payments false. |

PR #13 merged after checks and isolated staging. The merge commit has no file
differences from the tested staging candidate. The patch only adds fixed-status
billing diagnostics to pre-deploy CLI output and advances project versions. Billing,
authorization, pilots, prices and schema v8 remain unchanged.

The first production smoke run observed old API responses during deployment but
new v0.4.1 page content. It was not counted as a matching identity pass. A separate
fresh cache-busted read after Render reported live returned exactly:

- /api/version: version 0.4.1, environment production, commit 0301e31c18f087c1cadebbcd3557f6ddc2973876.
- /api/health: status ok, version 0.4.1, payments_enabled false.

The ordinary sign-in page rendered. The paywall is still OFF. No charges,
subscriptions, test customers, or new user accounts were created in this continuation.

## Passed verification

Normal beta PR workflow 37252257410 / job 111582123150 completed successfully for
candidate cf34432724b9aae2afa32987362a4df67f57eb86. From beta/:

1. `uv sync --frozen --dev`; `npm ci`; `.venv/bin/playwright install --with-deps chromium webkit` — Passed.
2. `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` — Passed.
3. `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` — Passed.
4. `.venv/bin/mypy landwolf`; `npm run typecheck` — Passed.
5. `npm run test:unit`; `.venv/bin/pytest -q -m 'not browser'` — Passed.
6. `.venv/bin/python scripts/check_postgres.py`; `.venv/bin/python scripts/check_restore.py` — Passed, disposable CI PostgreSQL only.
7. `npm run build`; `.venv/bin/pytest -q -m browser` — Passed.
8. `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` — Passed.
9. `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable`; `npm audit --audit-level=moderate`; `npm run secrets` — Passed.
10. `git diff --check`; `git status --short` — Passed.

Root workflow 37252257391: `PYTHONPATH=. pytest -q` — Passed in its separate environment.
Static preflight workflow 37252257447: `PYTHONPATH=. pytest -q tests/unit/test_deployment_preflight.py` — Passed.
Its legacy runtime staging/production preflight jobs were skipped by workflow conditions,
not counted as passes. Local diagnostic-specific tests: 22 passed; pinned Ruff passed.

## Unverified or blocked

- Live API authentication, live checkout, genuine webhook delivery and paid lifecycle:
  not verified, because the required runtime configuration remains missing.
- Owner UUID and authenticated owner/pilot runtime access: not verified. The direct
  hosted PostgreSQL query tool is blocked by the database's closed external allowlist.
  Do not open the database publicly; an owner-run read-only Shell query can obtain
  the existing account UUID without returning secrets.
- No attempt was made to circumvent the earlier blocked live-checkout browser task.
- One Render log read failed with a transient provider 503; its bounded retry
  succeeded. Direct public web-tool reads were unavailable; the browser's fresh
  GET-only check succeeded.

Production secrets were never retrieved into chat or committed to source. The
private invitation list and non-secret plan settings were not overwritten. Keep
payments disabled while the owner corrects the three required configuration names.
This report is a documentation-only commit, not another runtime deployment.
