# CRM contact opening and mobile login — v0.9.2

## Changes

- Opening a CRM contact now immediately shows a loading heading and moves focus
  into its detail section. The completed contact stays in view after rendering.
- Edit contact profile and account administration appear before the long facts
  list. Back to contacts restores list focus; failed requests offer a visible retry.
- On signed-out screens below 640 CSS pixels, the extra chat-only dock is hidden.
  One floating chat launcher remains at the bottom right. Signed-in navigation
  and tablet/desktop controls retain their existing behavior.
- No account, billing, authorization, database schema or email-delivery changes.

## Regression coverage

Chromium and WebKit at 390, 768 and 1440 pixels use 31 persisted contacts, open
an off-screen detail, assert focus and viewport visibility without test scrolling,
edit and save a profile, return to the list, and recover from an HTTP 503. Dock
checks cover signed-out and signed-in states, the 639/640 breakpoint, and a short
viewport. Emulation does not claim a physical iPhone keyboard test.

## Verification status

Candidate checks are in progress. Deployment and final results will be recorded
after observation in RELEASES.md and VERIFICATION.md.

## Resumed release

The original mobile candidate passed all gates in run 37422754074 (74 browser tests).
While paused, the Treasury parser repair shipped as production v0.9.1. The resumed
v0.9.2 release merges that repair and its regression test; it does not revert newer
production changes. Full combined checks and live promotion evidence follow.
