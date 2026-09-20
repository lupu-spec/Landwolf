# AGENTS.md

## Scope and precedence

These rules apply to the entire repository. A more-specific nested `AGENTS.md`
may add or strengthen requirements. Existing project commands and CI rules take
precedence over generic examples below. Never weaken a gate to make a change pass.

## Engineering standard

Use NASA/JPL-style defensive engineering, MIT Software Construction principles,
and the applicable Google language style guide. Priority: correctness, security,
reliability, readability, maintainability, performance.

- Make the smallest coherent change; preserve unrelated user changes.
- Read relevant code, tests, configuration, and interfaces before editing.
- Keep control flow and interfaces simple; use focused functions and narrow scope.
- Validate untrusted input and explicit invariants; fail safely and visibly.
- Check errors and important return values. Bound retries, loops, queues, recursion,
  memory growth, and external waits; use timeouts and reliable cleanup.
- Avoid hidden mutable state, magic values, unsafe casts, and needless dependencies.
- Follow repository formatters and style rules. Comments explain why or constraints.
- Preserve compatibility unless the task explicitly authorizes a breaking change.

## Required command discovery

Before changing code, inspect `AGENTS.md`, `README*`, CI workflows, build files,
lockfiles, and task runners. Use only commands supported by the repository.
Record the exact commands run and their exit status.

Common sources, in order: CI configuration; `Makefile`/`justfile`/task runner;
package scripts; language-native tooling. Do not install, upgrade, or regenerate
dependencies unless the task requires it.

## Mandatory verification gates

After a code change, run every applicable repository command in this order:

1. Format check (or formatter, followed by a clean diff review).
2. Lint and static analysis.
3. Type-check or compile.
4. Tests covering the change, then the full unit suite when practical.
5. Relevant integration/end-to-end tests.
6. Production build or package validation.
7. Security checks below.
8. `git diff --check` and `git status --short`.

Examples are discovery hints, not permission to guess commands:

| Stack | Required commands when configured |
| --- | --- |
| JavaScript/TypeScript | `npm run format:check`, `npm run lint`, `npm run typecheck`, `npm test`, `npm run build` |
| Python | `ruff format --check .`, `ruff check .`, `mypy .` or `pyright`, `pytest` |
| Go | `gofmt -l .`, `go vet ./...`, `go test ./...`, `go build ./...` |
| Rust | `cargo fmt --check`, `cargo clippy --all-targets --all-features -- -D warnings`, `cargo test --all-features`, `cargo build --release` |

A gate passes only when its command exits successfully. A timeout, crash, skipped
suite, missing tool, unavailable service, or partial run is **not** a pass. Fix
failures caused by the change. Report unrelated/pre-existing failures separately.
If a gate cannot run, state the exact command, reason, and resulting verification gap.

## Test requirements

- Every behavior change requires tests for normal, boundary, invalid-input, and
  failure cases; every bug fix requires a regression test when feasible.
- Test public behavior, important integrations, and error paths—not merely lines.
- Critical calculations and authorization decisions require invariant/property
  tests and deterministic fixtures when supported.
- Do not delete, weaken, skip, quarantine, or broadly mock a failing test to pass.
- Do not update snapshots or golden files without reviewing and explaining changes.

## Security gate

Before completion, review the diff and run configured secret, dependency, and
static security scanners. At minimum verify:

- no credentials, tokens, private keys, personal data, or sensitive values appear
  in source, fixtures, logs, errors, command output, or the diff;
- all trust-boundary inputs are validated; SQL is parameterized; shell arguments
  are safely constructed; output is contextually escaped;
- authentication and authorization are enforced server-side with least privilege;
- cryptography uses maintained platform/library primitives—never custom crypto;
- sensitive operations avoid unsafe deserialization, path traversal, SSRF, XSS,
  CSRF, injection, insecure redirects, and accidental information disclosure;
- new dependencies are necessary, pinned/locked as the repository requires, and
  reviewed with the configured vulnerability/audit command.

Do not expose secret values while checking them. Report names/status only.

## Release versioning

Every deployment must follow `RELEASES.md`: assign a new runtime version, run the
required gates, and record the observed version, commit, environment, UTC time,
deployment ID, changes and verification evidence. Keep production and beta status
separate. Preserve the append-only deployment history; never call a pushed branch
deployed until the live service is observed. Do not reuse versions for changed code.

## Completion and evidence

Never claim or imply that code is verified, tests pass, a build succeeds, a bug is
fixed, or a service works unless the relevant commands actually ran to completion
and succeeded in the current environment after the final change.

The final report must list:

- files/behavior changed;
- each verification command actually run and its result;
- failures, skipped/unavailable gates, and remaining risks.

Use precise labels: **Passed**, **Failed**, or **Not run**. “Not run” is never
equivalent to “Passed.” Do not fabricate command output, execution, coverage, or
external-system status.
