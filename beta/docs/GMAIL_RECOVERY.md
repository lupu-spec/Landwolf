# Support Gmail password recovery

Status: **live and enabled in production**, v0.9.3, observed 2026-10-10 UTC.
Both real reset-email paths and link completion passed. Staging runs the same
runtime with delivery disabled. See the verification record below.

The login page and signed-out Romulus/Remus form use `/api/auth/recovery`.
Signed-in chat uses `/api/account/password-reset` and the account email stored on
the server; it cannot override the recipient. Both paths use the same mailer.
Gmail messages come from **LandWolf Support <support.landwolf@gmail.com>**, with
replies directed to that mailbox. Only the requesting account receives its reset
link; no support copy, CC or BCC is added. Chat never receives passwords or tokens.

## Configuration

1. Sign into the Google account `support.landwolf@gmail.com`. Enable two-step
   verification if needed, then create an app password named **LandWolf recovery**
   at <https://myaccount.google.com/apppasswords>.
2. In the existing production service's Render Environment page, add the secret
   `LANDWOLF_GMAIL_APP_PASSWORD` with that app password. Choose **Save only**.
   Never paste the password into chat, Git, logs, screenshots or client code.
3. After candidate validation, set `LANDWOLF_MAIL_FROM=support.landwolf@gmail.com`
   and `LANDWOLF_MAIL_PROVIDER=gmail` together with the Gmail-capable release.
   Do not set the provider on the old runtime: it rejects unknown providers.
   No `LANDWOLF_MAIL_API_KEY` is required for Gmail. Keep unrelated variables.
4. Verify a reset request from the login page and one from Romulus/Remus using an
   owner-controlled test account. Inspect sender, reply-to and recipient; open each
   link privately, reset, verify old sessions are revoked and reuse is rejected.
   Never use the owner account merely as a test or expose a reset link in evidence.

Google may not offer app passwords for accounts with Advanced Protection or other
account restrictions. Report that blocker rather than lowering account security.
Changing the Google account password revokes its app passwords. See
<https://support.google.com/accounts/answer/185833>.

Delivery uses fixed `smtp.gmail.com:465`, certificate-verified implicit TLS,
10-second socket timeouts and a worker thread. Render's existing production
Starter service supports SMTP; free web services (including current staging) block
SMTP ports. Do not upgrade staging or incur charges automatically. Full isolated
transport/API/browser tests run in CI; real mailbox delivery must be observed on
the paid service. See <https://render.com/docs/free>.

The existing rate limits, generic account-existence response, hashed token
storage, 30-minute expiry, one-use consumption and session revocation remain.
Authentication, TLS, network and recipient refusal failures invalidate the issued
token and log a fixed warning without secrets. SMTP is not automatically retried
because a lost acknowledgment could duplicate mail. A 202 response means the
request was accepted, not proof of inbox delivery. Gmail quotas still apply.

## Rollback

Set `LANDWOLF_MAIL_PROVIDER=disabled` before rolling back to a runtime without
Gmail support. Existing passwords and accounts need no migration. Remove/revoke
the app password if abandoning Gmail delivery. Never reset the database.

## Release and real-delivery verification — 2026-10-10 UTC

Production commit `e7baf8719fa6092013903cf1a53dd1cebcffbd07`, deployment
`dep-db4qq25ckfvc73fu2fc0`, became live at **03:13:09 UTC**. Its tree matches final
staging candidate `5fa9f2552ea854292dc15077d2a9417dba022aa2` exactly. Before
promotion, the signed-in Render Recovery page showed the existing production
database's three-day point-in-time recovery window and an enabled Restore
database control. No restore, export, network or database change was performed.
Schema remains 11; rollback needs the mail-provider change described above.

**Passed:** final [full gates](https://github.com/lupu-spec/Landwolf/actions/runs/38018712379),
[PR gates](https://github.com/lupu-spec/Landwolf/actions/runs/38018713829),
[legacy suite](https://github.com/lupu-spec/Landwolf/actions/runs/38018713905),
[preflight](https://github.com/lupu-spec/Landwolf/actions/runs/38018713915),
[staging hosted checks](https://github.com/lupu-spec/Landwolf/actions/runs/38018712345)
and [production hosted checks](https://github.com/lupu-spec/Landwolf/actions/runs/38019710454).
The hosted check now requires production delivery enabled and staging delivery
disabled; its synthetic `example.com` accounts never request email.

Each configured command below **Passed** (exit 0) on the final candidate in CI:

| Commands, from `beta/` unless stated | Result |
| --- | --- |
| `uv sync --frozen --dev`; `npm ci`; `.venv/bin/playwright install --with-deps chromium webkit` | Passed |
| `.venv/bin/ruff format --check landwolf tests scripts`; `npm run format:check` | Passed |
| `.venv/bin/ruff check landwolf tests scripts`; `npm run lint` | Passed |
| `.venv/bin/mypy landwolf`; `npm run typecheck` | Passed |
| `npm run test:unit`; `.venv/bin/pytest -q -m 'not browser'` | Passed: 16 frontend, 488 backend |
| `.venv/bin/python scripts/check_postgres.py`; `.venv/bin/python scripts/check_restore.py` | Passed: disposable PostgreSQL, exact 29-table restore |
| `npm run build`; `.venv/bin/pytest -q -m browser` | Passed: 74 browser tests |
| `.venv/bin/python -m build`; `.venv/bin/python scripts/check_package.py` | Passed |
| `.venv/bin/bandit -r landwolf`; `.venv/bin/pip-audit --local --skip-editable`; `npm audit --audit-level=moderate`; `npm run secrets` | Passed |
| Repository root `git diff --check`; `git status --short` | Passed |
| Legacy environment `PYTHONPATH=. pytest -q` | Passed: 53 tests |
| `.venv/bin/python scripts/check_hosted_staging.py --environment staging` | Passed: exact release, HTTPS/health, four browser journeys, persistent sessions and coverage privacy |
| `.venv/bin/python scripts/check_hosted_staging.py --environment production` | Passed: exact release, custom-domain HTTPS/health, mail/billing enabled, four browser journeys, persistent sessions and coverage privacy |

Local release preparation also passed `uv lock --check`, the Python format/lint
checks, and `.venv/bin/pytest -q tests/test_version.py tests/test_gmail_recovery.py
tests/test_recovery.py tests/test_account_profile.py` (55 tests). No dependency
upgrade or schema migration was introduced. Version metadata agrees in all five
versioned files. Full command history from candidate development remains in
[VERIFICATION.md](VERIFICATION.md).

**Passed: real mailbox and reset API checks.** An isolated verification account
using an owner-controlled support Gmail plus alias received two emails, at
03:15:17 and 03:15:52 UTC. The first was requested through the signed-out
login/recovery route; the second through the signed-in Romulus/Remus reset route.
For each message, From was `LandWolf Support <support.landwolf@gmail.com>`,
Reply-To was `support.landwolf@gmail.com`, To was solely the verification account,
and CC/BCC were empty. Each link used the canonical `https://landwolf.ai/` origin.
Each reset completed (200), token reuse was rejected (400), the old password was
rejected (401), the previous session was invalidated, and the new password worked.
The verification account was logged out; temporary credentials were removed.
No customer or owner password was changed. No token or credential is in evidence.
The deployment-window mail-failure log query returned no entries.

Only `LANDWOLF_MAIL_FROM` and `LANDWOLF_MAIL_PROVIDER` were merged into production
configuration, retaining the owner-saved app password and every unrelated value.
This environment update itself triggered the deployment; no duplicate deploy was
requested. Payments remained enabled in production health and hosted checks.

**Limits and resolved verification failures:** the local runner cannot retrieve
custom-domain JSON (returns a Site Unavailable HTML page); hosted custom-domain
checks passed independently. Initial private API tests incorrectly paired the
custom-domain Origin with the service host and received 403 before account
creation. Using the already-allowlisted service origin consistently resolved the
test setup error; no application security setting changed. Actual mail/reset
completion used the production API, while browser journeys and UI wiring were
covered by CI. No physical-device or external-recipient deliverability claim is
made. Gmail quotas and account restrictions remain applicable.

**Failed, unrelated upstream check:** disposable `.venv/bin/python -m
landwolf.cli sync` exited 1 because Arkansas COSL returned HTTP 500. Other listing
adapters returned validated counts (MN 4, TX 30, USDA 19, Treasury 21, IRS 1,
AK 170, MI 28). This was not an email failure. No source adapter, last-good
snapshot or quarantine policy was modified. Local browser execution was **Not
run** on this release because the executables were absent; the complete hosted
Chromium/WebKit suite passed. Production SQL inspection was unavailable through
the connector because the external allowlist is empty; that boundary was kept.
