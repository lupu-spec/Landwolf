# Billing setup diagnostics — v0.4.1

This patch diagnoses configuration without weakening the live-only billing gate.
It does not change Stripe calls, prices, the paywall, pilot eligibility, account
privileges, or database schema. No secrets or recipient list are in source.

`python -m landwolf.cli init-db` now prints one `Billing process environment status:`
JSON line before constructing Settings. Output is restricted to a fixed list of
variable names and fixed status labels. No values, secret fragments, lengths,
hashes, customer identifiers, owner UUIDs, or recipient addresses are printed.
There is no public diagnostic endpoint. Existing Settings validation still runs
and still refuses missing, non-live, or incomplete billing configuration.

Statuses distinguish missing/empty variables, surrounding or embedded whitespace,
quotes, masked display copies, publishable keys, sandbox server keys, wrong
prefixes, too-short values, oversized values and ambiguous case variants. A
`format_ok_not_authenticated` result is only a shape check, not successful Stripe
authentication or webhook verification. Legacy unprefixed variables are inspected
for diagnosis only; they never become runtime key fallbacks.

The report describes the process environment, not .env files or programmatic
Settings overrides. Case-insensitive lookup follows the application's environment
naming convention, but multiple differently cased keys are reported as ambiguous.
Only fixed names are emitted, so unrelated environment entries cannot appear.

## Verification before publication

On the local copy of the already tested v0.4.0 runtime:

- `PYTHONPATH=. pytest -q tests/test_billing_diagnostics.py`: 22 passed.
- Repository-pinned Ruff 0.16.7: `ruff format` on the new diagnostic module, CLI
  integration and tests left all three unchanged; `ruff check` passed.
- Project versions were advanced to 0.4.1 in runtime, Python/npm metadata and
  lockfile project entries only. Dependency versions were not regenerated.
- Full hosted beta/root PR gates and isolated staging remain required before
  promotion. A local pass is not a deployment or an activation.

The production key-format failure was reproduced in deployment
`dep-db1frqnavr4c73bne27g` at 2026-10-05 01:31:40 UTC. Billing was restored to
`false`; recovery deployment `dep-db1fsbegekts73dkraqg` was reported live at
01:32:58 UTC. This patch is intended to identify the cause from statuses instead
of asking the owner to repeat an undifferentiated key correction.
