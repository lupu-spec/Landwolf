# Support Gmail password recovery

Status: candidate prepared; not deployed or enabled. Real delivery still requires
the support mailbox credential and an observed inbox test.

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
