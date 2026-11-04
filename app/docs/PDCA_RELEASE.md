---
name: pdca-software-release
description: Apply Toyota-inspired Plan–Do–Check–Act to software fixes, customer workflows, and release QA. Use when diagnosing escaped defects or verifying a release end to end, with evidence tied to the deployed revision.
---

# PDCA for software development and release QA

This is a software adaptation, not an official Toyota certification. Apply it within the user's authorized scope and the repository's existing gates. It adds no permission requirement when deployment is already authorized.

## PLAN — observe the actual work

Trace the failing user journey from its actual entry point through storage, approval, queue, worker, review and delivery. Record observed facts separately from hypotheses. A synthetic happy path does not establish that a different entry path works. Inspect the real defect where authorized, without copying customer data into public tests.

Write a short evidence ledger before editing: problem, current behavior, desired outcome, likely cause, countermeasure, acceptance checks and release/rollback boundaries. Derive checks from customer outcomes and trust boundaries, not from the proposed implementation. Include alternate entry paths, retries, offline workers, failure states, access isolation, and preservation of existing records where relevant. Keep work scoped; do not automate an unverified manual path.

## DO — controlled countermeasure

Implement the smallest complete workflow correction. Preserve the original brief, immutable dispatch identity, approval audit and tenant ownership. Never infer account ownership from an unverified email address. Generated code remains isolated until reviewed. A generated patch, queued task or syntax check is not a working deliverable.

Add regression tests that fail for the observed defect and independent acceptance checks before running an implementing model. Do not let generated code change its own acceptance tests. Make failures and waiting states visible; bound retries and stop duplicate execution. Record failed attempts as well as successful ones.

## CHECK — establish evidence

Run required repository gates on the final candidate; retain commands, exit statuses, revision/artifact hashes, UTC time, environment and evidence locations. Mark each criterion Passed, Failed, or Not run. Missing evidence, a skipped test, a timeout, stale build or fixture-only check is never Passed.

Verify the complete user journey through the actual UI and persisted state. Check the original entry path and another customer/account boundary. For async work, follow one correlation chain from request ID to approval, dispatch, runner job, result and delivery. Confirm refresh/reload preserves progress. Test real acceptance behavior, not just HTTP 200 or a success toast. For generated webpages, exercise functionality and visually inspect desktop/mobile output; a patch download alone does not meet a request for a usable webpage.

Treat local tests, staging checks and production checks as distinct evidence. Test the release candidate in staging before promotion. Build/deploy the same tested code or explicitly prove runtime tree equality; after any code change repeat affected checks and repository-required gates. Verify version, commit and environment on the live deployment and run non-destructive production smoke tests before declaring completion.

## ACT — standardize or stop

If required checks fail or cannot run, stop promotion (ANDON), state the exact blocker and return to PLAN or DO. Do not weaken tests, silently substitute fixtures, or repeatedly retry an unchanged failure. Fix what is within scope; ask only for genuinely missing authorization or information.

After successful checks, deploy only within existing authorization. Verify the live result, record rollback compatibility and standardize the successful countermeasure in regression tests and focused operational documentation. Keep unsuccessful evidence. If production smoke checks fail, stop rollout and use the authorized safe rollback/remediation path; never reset user data to get green checks.

Finish with what changed, what was actually verified, where the user can see the result, and any remaining limitation. Separate “generated,” “tested,” “reviewed,” “deployed,” and “delivered.” Never claim a whole process works from evidence for one component.

## Source principles

- [Toyota Industries Commercial Finance: PDCA](https://www.toyotacf.com/plan-do-check-act-the-pdca-cycle/): compare actual conditions with a target, investigate causes, evaluate countermeasures and standardize successful processes.
- [Toyota Motor Corporation: Production System](https://global.toyota/en/company/vision-and-philosophy/production-system/): stop abnormalities at the source, build quality into work, improve the process before automating it, and keep work and information flowing.

The software-specific evidence, staging, tenant-isolation and rollback requirements above are this skill's adaptation of those principles.
