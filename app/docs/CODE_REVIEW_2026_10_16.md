# LandWolf repository review — October 16, 2026

Baseline: `34649586357702f12ed0d183392faff896658476` (main, v0.13.1).
Candidate: v0.14.0. This is a repository-wide structural/static review plus
risk-focused manual inspection and regression testing; it is not a security
certification or a claim that every execution path was manually verified.

## Scope and evidence

[The inventory](CODE_REVIEW_INVENTORY.json) records 222 code/configuration files,
42,269 lines: 69 active production files, 75 verification/configuration files,
and 78 archived files. It includes every tracked/candidate Python, TypeScript,
JavaScript, HTML, CSS, shell, YAML and Dockerfile, with SHA-256 hashes. Dependency
contents, generated bundles and binary assets are excluded. Python files were
parsed for syntax and structure. Runtime review focuses on authorization,
payment/trial invariants, ingestion/provenance, research, financial calculations,
client rendering, deployment configuration and the changed UI lifecycle.

The active stack is FastAPI/SQLAlchemy with strict Pydantic contracts, an esbuild
TypeScript/Leaflet UI, locked dependencies, and separate legacy requirements.
The existing Docker runtime is non-root. Production uses the existing service and
database; automatic deploys are disabled. The frontend composition file and the
backend application factory remain the largest integration points.

## Findings and actions

| Priority | Finding and evidence | Action / recommendation |
| --- | --- | --- |
| High maintenance | `web/app.ts` mixed navigation, shared DOM/link utilities, source contracts, filter state and coverage rendering across 2,570 lines. | Extracted `coverage.ts`, `source-list.ts`, `source-health.ts`, `source-links.ts` and `dom.ts`. Main composition file is now 2,316 lines. Coverage state is private and cleared at sign-out; original link restrictions are preserved. Continue with one tested feature extraction per change. |
| Medium maintenance | TypeScript compilation included only `web/app.ts`, relying on reachable imports to bring other files into scope. | Changed the include to `web/*.ts`, so standalone helpers are checked too. Strict flags remain enabled. |
| Medium release | New stylesheet could be left out of a distributable without a packaging failure. | Build copies `graphite.css`; package validation now requires it and the new source/test modules. No dependency added. |
| Medium usability | Source status required reading expanded cards; date rendering lacked year/time-zone context. | Three-column disclosure list; pure tested age rules; explicit directory/missing states; date/year/time-zone labels; accessible status names and keyboard expansion. |
| Medium maintenance | `styles.css` has 3,546 lines and repeated selectors for original, mobile, dock and finance refinements. | Added one bounded graphite stylesheet instead of changing many cascade-sensitive rules. Follow-up: consolidate feature CSS with browser screenshots and computed-style comparisons, preserving source order and print rules. |
| Medium maintenance | Backend `create_app` spans 746 lines; CRM register functions span 349/316 lines; research route registration spans 219 lines. | Route grouping is a next candidate, using injected existing services and unchanged dependency/transaction order. Large factory size alone is not a runtime defect. Avoid mixing payment/auth route movement into an appearance release. |
| Medium maintenance | Several API responses use `dict[str, Any]`, and the browser independently defines response shapes. | Introduce explicit response models per endpoint, then generated/shared frontend contracts; add compatibility fixtures before enforcing stricter output. Do not silently remove fields or weaken current input models. |
| Medium operations | Source import age, the six-hour stale diagnostic, provider availability and publisher dates are different facts. | The requested colors use last successful import only. Expanded details retain latest failures and history. Documentation explicitly explains a green age indicator can accompany a failed latest attempt. |
| Low legacy scan | Bandit B105 in `archive/legacy/app/core/config.py:68`. | Reviewed: comparison rejects a known placeholder value in staging/production; it is not a deployed hard-coded credential. Archive retained unchanged and separately tested. Do not suppress the scanner or restore this runtime. |
| Low process | Dependency/build inputs use versioned packages but action references use version tags and base images use mutable major tags. | Follow-up: pin reviewed action/image digests with a scheduled update process. Avoid freezing old versions indefinitely or changing infrastructure during this UI release. |

## Protected behavior inspected

- `auth.py`/`config.py`/`main.py` enforce server authentication, hashed opaque
  sessions, explicit origins/hosts, CSRF, bounded bodies and no-store API responses.
- `admin.py`, CRM, finance and `/api/sources` enforce owner authorization on the
  server. Hiding navigation is not the authorization boundary.
- `billing.py` verifies live configuration, signed timestamps, account/customer
  relationships and event idempotency; trial/feedback logic retains explicit
  consent, deadlines, advance notice, cancellation and CRM/pilot exemptions.
- `catalog.py`/`national.py`/`trust.py` retain bounded requests, restrictive URLs,
  independent last-good snapshots, quarantine and known-coordinate provenance.
- `analysis.py` uses seeded scenarios and bounded inputs, labels assumptions,
  distinguishes missing values and does not infer market value from asking price.
- Finance uses integer cents/Decimal rounding, owner checks, duplicate import
  fingerprints and scenario labels; existing cash-flow assumptions are retained.
- Active frontend provider text is rendered with text nodes. The extracted
  link helper still rejects credentials, non-HTTPS, ports and unapproved hosts.
  Archived template rendering was inspected separately and remains non-production.

No newly confirmed critical runtime defect was established by these checks.
A clean scan and passing deterministic suites do not prove upstream availability,
physical keyboard behavior, complete property coverage or absence of vulnerabilities.

## Refactoring policy and next work

The implemented restructuring follows feature boundaries without database/schema,
account, billing-runtime, provider or research changes. Further work should extract
search/map state, property/scenario controllers and backend route groups in separate
reviewable releases, then consolidate CSS and API contracts. Each step needs the
existing browser, authorization, calculation and disposable database tests.
[AI change guide](AI_CHANGE_GUIDE.md) gives the exact module map and protected rules.
Do not perform a framework rewrite simply to reduce line counts.

## Verification and deployment status

Exact local commands and exit statuses are in [VERIFICATION.md](VERIFICATION.md).
At preparation time: 24 frontend, 572 backend/API and 53 legacy tests passed;
active Python Bandit, Python dependency audit, npm audit and secret scan passed.
Local browser setup failed with a corrupt download; the new browser test could
not launch a missing executable. Disposable PostgreSQL/Docker are unavailable.
These are unresolved gates until hosted CI supplies the required evidence.
Staging/production promotion must not precede those gates. Current live v0.13.1
remains authoritative until an observed v0.14.0 deployment is entered in RELEASES.md.
