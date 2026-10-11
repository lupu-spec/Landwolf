# Live billing verification — 2026-10-05 UTC

## Candidate, not a live billing deployment

The complete isolated candidate gate ran on source commit
`af1a72c882059a8fb9539d2bf26fc5025e993d3e`:
https://github.com/lupu-spec/Landwolf/actions/runs/37245854162

The workflow initially checked out `4720eed8600cc6fb9dd4598d9e31cdca983d459f`,
applied the reviewed two-file repair, and checkpointed the exact tested source
before running the gates. The artifact's `candidate-commit.txt` records that SHA.
Evidence artifact: `11319495784` (hosting retention is three days).

## Resolved browser regressions

- `beta/web/styles.css`: replace the fixed header height with a minimum height
  and allow header flex items to wrap. Enlarged text must not push Sign out past
  the viewport. Existing Chromium/WebKit responsive and 200%-text tests remain.
- `beta/tests/test_browser.py`: assert the exact six navigation labels, including
  the intended Membership addition, rather than the obsolete five-button count.
  Saved-feature absence and research-handoff assertions remain unchanged.
- No tests were removed, skipped, or broadly mocked to address these failures.
  The successful 1440px enlarged-text screenshot was also inspected.

## Exact verification commands

All commands below completed with exit status 0 in GitHub's locked Python 3.12 /
Node 24 environment. Application commands ran from `beta/` unless specified.

| Check | Commands | Result |
| --- | --- | --- |
| Locked install | `uv sync --frozen --dev`; `npm ci` | Passed |
| Format | `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed |
| Lint | `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed |
| Types | `.venv/bin/mypy landwolf`; `npm run typecheck` | Passed |
| Unit/API | `npm run test:unit`; `.venv/bin/pytest -q -m 'not browser'` | Passed |
| PostgreSQL | `.venv/bin/python scripts/check_postgres.py` | Passed; disposable CI database only |
| Restore rehearsal | `.venv/bin/python scripts/check_restore.py` | Passed; disposable CI database only |
| Browsers | `.venv/bin/playwright install --with-deps chromium webkit`; `npm run build`; `.venv/bin/pytest -q -m browser` | Passed |
| Package | `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed |
| Security | `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable`; `npm audit --audit-level=moderate`; `npm run secrets` | Passed |
| Diff | Repository-root `git diff --check`; `git status --short` | Passed |

Local preliminary checks were not substituted for these gates. Local formatting
and frontend build succeeded, but the local browser attempts could not run: broad
collection lacked Hypothesis, and explicit browser tests lacked installed browser
executables. These environment failures were superseded by the full hosted run.
The root/legacy PR checks are separate and must be observed before promotion.

## Production preparation actually performed

The authenticated Render connector successfully merged the non-secret live merchant,
recurring price, portal configuration and private marketing-reservation settings
onto the existing production service. `LANDWOLF_PAYMENTS_ENABLED` remains `false`.
No recipient addresses or secret values are included in this report or source.

The environment-update action automatically redeployed the existing production
branch, not the billing candidate. Render deployment `dep-db1ei5mgekts73df8i0g`
reported `live` at `2026-10-05T00:02:59Z`, commit
`802e1248d2c4d1e248a87f625c377ecfe22b8cf1`. No billing-schema migration or billing
activation was requested. An independent HTTP body/version observation was not
obtained through the available public fetch tools in this step.

The live recurring USD $29/month and $299/year prices, existing live webhook URL
and active live portal with period-end cancellation were re-read from Stripe.
The separate one-time $299 price is not used. No charges or subscriptions were
created in this step.

## Outstanding release gates

- Saved browser state still redirects to Render login despite the user's manual
  sign-in; the direct Render connector works independently.
- Live server key and the matching existing webhook signing secret must be placed
  privately in Render; do not send them through chat or GitHub.
- Confirm the existing owner account UUID and its match to the intended owner.
- Confirm a recoverable production backup, then deploy and observe the exact
  candidate in isolated staging before production promotion.
- Validate real runtime live-key permissions, webhook signature handling and
  ordinary/owner/pilot entitlement behavior. The reserved email list alone is not
  proof of identity and does not start the pilot clock.
- A live paid purchase and genuine paid-subscription lifecycle remain Not run;
  synthetic CI fixtures do not establish that real billing works.

Follow `LIVE_BILLING.md` for activation and the schema-v8 rollback boundary. Do
not mark the paywall live merely because source tests or Stripe objects pass.
