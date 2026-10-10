# Investor feedback pilot — v0.4.0-beta.7

This release adds an invitation-only LandWolf feedback cohort. It was deployed to staging and production on 2026-10-04 after hosted gates and live HTTPS/browser checks passed. See [the release evidence and limits](INVESTOR_PILOT_RELEASE.md). It is not a Stripe trial, mailing campaign, or evidence of customer demand.

## Owner workflow

Configure `LANDWOLF_OWNER_ACCOUNT_ID` to the existing owner's immutable account UUID. Never derive owner privilege from submitted email or a browser flag. Sign in as that account, open Feedback, and invite selected existing accounts using the owner table. Participants see the invitation after sign-in; no email is sent. Review individual responses in the owner feedback report. Owner reads and writes require server authorization; mutations additionally require the existing same-origin and CSRF checks.

## Participant terms and experience

The user explicitly accepts versioned terms and submits a starting survey. Their term starts on that successful transaction and ends three calendar months later, at the same UTC time, with month-end dates clamped (November 30 → February 28/29). No payment method is collected, no subscription is created, and no automatic charge occurs. Acceptance and submissions are idempotent for identical payloads; they cannot restart or extend the term.

Further surveys become due at days 14, 30, 60, and 85. Each has up to seven days of grace, ending earlier if the fixed pilot term expires. Sign-in and a visible-page 60-second poll display due reminders. Polling does not extend idle session expiry. No background email scheduler or outbound message delivery is implemented.

The survey asks about the last attempted task, blockers, one requested feature, why it matters, priority, and experienced value. Honest “not used” and “no changes” responses are allowed. Rating is required only after reported use. Text is bounded, blank required answers are rejected, and feedback is rendered as text rather than HTML. There are no token-consuming AI calls.

After grace expires, server-side access pauses for search, source data, property details, research, analysis, new Hunts, and Hunt matches/events. Completing the earliest outstanding survey restores access if no other survey is overdue and the original term remains active. Expiry or owner revocation ends cohort access. Session management, account recovery, feedback, support links, and existing Hunt list/edit/delete remain available. Surveys and Hunt records are not deleted when access stops.

Existing non-cohort users retain their current access. A revoked invitation that was never accepted does not reduce legacy access. The existing rebuilt application keeps payments disabled; this change does not introduce a global paywall or alter legacy Stripe code. Owner or separately granted complimentary access is an explicit independent override; the feedback status endpoint reports that override consistently. Do not interpret such an override as a trial renewal. Accounts already holding independent overrides cannot enroll.

## API and data

- GET `/api/feedback`: signed-in user's state, due survey, dates and effective access.
- POST `/api/feedback/accept`: versioned terms, explicit acceptance, baseline answers.
- POST `/api/feedback/responses`: earliest due survey key, schema version and answers.
- GET `/api/admin/feedback`: bounded owner cohort report.
- GET `/api/admin/feedback/responses`: bounded owner responses and audit events.
- POST/DELETE `/api/admin/accounts/{account_id}/feedback-pilot`: owner invitation/revocation.

There is no client-selectable account ID for responses. Schema v7 adds enrollment, response and audit tables, preserving existing accounts, sessions, listings, and Hunts. One enrollment history per account prevents replayed invitations creating fresh trials. Responses have a composite unique key; transactions serialize acceptance, response, and revocation. Audit events contain lifecycle actions without copying response text into operational logs.

Run the existing `python -m landwolf.cli init-db` predeploy migration under the normal deployment process. The migration is additive from schema v6 and idempotent. Older images that reject schema v7 require a compatible forward fix or an approved backup restore; do not drop feedback tables or downgrade the marker to simulate rollback. PostgreSQL migration/restore verification must pass in a disposable environment before deployment.

## Validation and release gates

Market research establishes 14 publicly identifiable prospects across three segments, not confirmed pain or willingness to pay. Free access and mandatory surveys test product needs; they do not establish paid implementation demand. Track voluntary repeat usage separately from required submissions.

The attached tests cover authorization, explicit consent, fixed calendar expiry, grace boundaries, due-order enforcement, idempotency, malformed input, cross-account isolation, transaction rollback, migration preservation, reminder idle behavior, and UI policy. Mobile/desktop participant journeys and a delayed-startup regression passed in the 28-test hosted browser suite. Disposable PostgreSQL cohort transactions and 19-table backup/restore passed. Live version/health and four browser journeys per deployed environment were observed. Local browser installation remained unavailable and was not counted as a pass.

No real investors were enrolled and no outreach or invitations were sent. The authorized rollout retained existing services/accounts and applied additive schema v7. One synthetic non-cohort smoke-test account remains in each environment. Owner account binding was not changed; live owner login and real participant enrollment were not exercised.
