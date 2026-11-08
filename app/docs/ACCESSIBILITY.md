# Accessibility PDCA evidence and release plan

Target: WCAG 2.2 A and AA practical accessibility improvements, without a legal
certification or claim of complete conformance.

## Plan — baseline 2026-11-06

Observed production: 0.23.1, d6821ecbd6941823a855b6faf7b7a519967f56c2,
HTTPS /api/health reports ok. Candidate starts at repository main
5f35873665e1c15401f579b4e79da3ed41518e71.

Inspect public pages, sign-in/registration/recovery, search/list/map, property
and scenario dialogs, research, Hunts, feedback/membership and owner tools on
mobile and desktop in light/dark themes. Existing markup includes native dialogs,
labels and list/map switches; behavior and contrast still need measured checks.
No accessibility statement or axe regression suite exists in the baseline.

Countermeasures will follow observed audit failures, preserving authentication,
entitlements, source provenance, user data and the graphite/silver identity.
Acceptance: no WCAG-tagged axe violations in the covered states; keyboard-only
navigation, visible unobscured focus, dialog Escape/return focus, map list access,
error announcements, reduced motion and mobile reflow checks. Retain axe incomplete
results for human review. Automated success is not complete WCAG conformance.

Release boundaries: no schema changes; same candidate must pass repository gates,
hosted CI and staging acceptance before production. Keep existing infrastructure.
Prior compatible UI release is the rollback candidate; never reset customer data.

## Manual assistive-technology checklist — Not run

Record tester, date, exact runtime commit, browser/OS, assistive technology and
Passed/Failed for each item. Test NVDA/Firefox or Chrome and VoiceOver/Safari,
including iOS/Android physical devices where available.

- Follow skip link; read landmarks, heading hierarchy, page titles and active view.
- Complete sign-in, registration, recovery with keyboard and password manager;
  paste passwords; submit invalid/empty values and server failures. Confirm errors
  identify the field, explain correction and are announced without losing input.
- Traverse every dock item, filter, list page, source link and map/list switch;
  confirm focus is visible and not covered by the dock/chat/header.
- Open property details, Advanced scenarios and nested help; traverse controls,
  Escape each layer and confirm focus returns to the opener. No keyboard traps.
- Use List for every mapped or unmapped result, open details and source records;
  confirm no research action requires dragging, map gestures or visual coordinates.
- Complete research and Hunt creation/editing, empty results, failed requests and
  retries. Confirm loading, counts, errors and saved state announcements.
- Review owner CRM forms, tables, account actions, finances and coverage; verify
  role boundaries remain enforced. Do not perform destructive production actions.
- Test 200% text, 400% zoom/320 CSS-pixel reflow, custom text spacing, landscape,
  forced colors and reduced motion. Check dialogs and validation at each setting.
- Verify chart meaning is available in text/tables, meaningful image alternatives,
  contrast and focus in both themes, and touch targets/spacing on a physical phone.
- Follow Accessibility and support links. Review third-party maps, checkout and
  external source documents separately; do not infer their conformance.

## Do — candidate 0.24.0

Observed baseline axe failures: visible/accessibility-name mismatch on coverage,
CRM, chat and CRM statistics; invalid aria-pressed on the mobile results container;
non-focusable scrolling finance tables; insufficient contrast on dark map attribution.
Fixes preserve existing actions and expose readable names, region semantics, keyboard
scrolling and opaque theme-aware map credits. Main/skip-link targeting, result-count
announcements, research/auth error descriptions, reduced-motion programmatic scrolling,
forced-color focus and an accessible public statement are included.

Baseline public production scan: 12 page/viewport states; the desktop home launcher
failed label-content-name-mismatch. Authenticated baseline: four phone/desktop and
light/dark fixture journeys failed. Original JSON is retained in local audit evidence.
These fixture accounts do not establish authenticated production coverage.

Test development failures retained: initial exact research label was incorrect; next
attempt needed to switch from the property-prefilled coordinate mode to address mode;
one scan overlapped npm ci and lost its axe file. The motion unit test initially tried
to mock a missing window property; corrected with explicit isolated browser stub.

## Check and Act — observed release

- Candidate: `99aa3d68a74dd4370ce398478c1c34dd7962d938`; [PR #54](https://github.com/lupu-spec/Landwolf/pull/54).
- Staging: `f904d5e34a7a9b1a8b82e194403a8392a54e9294`, Render `dep-dbn05kjrjlhs73ckrm90`, live 2026-11-06 16:41:03 UTC.
- Production: `18b53c81a3a3a662b9dbd7eb1681dbd3b9ba1718`, Render `dep-dbn09915efls738ohvug`, live 2026-11-06 16:48:47 UTC.
- All three commits have the identical complete tree `748101bc119db865df4adfa610155342454c0662`. Runtime 0.24.0; schema 18 unchanged.

Corrects visible/accessibility-name mismatches, invalid result-toggle semantics,
unnamed groups, keyboard access to finance tables, map-credit contrast, public
canvas colors, focus hidden by floating controls, and long-account text reflow.
Adds error/help associations, result announcements, reduced-motion scrolling,
map List guidance and the public `/accessibility` statement. Existing native
dialog and focus-return behavior is regression-tested. Authentication, billing,
entitlements, customer data and infrastructure are preserved.

Final application [CI 42247666585](https://github.com/lupu-spec/Landwolf/actions/runs/42247666585)
passed 782 backend/API, 28 frontend and 172 browser cases, separate exact header
comparison, PostgreSQL integration, disposable backup/restore across 49 tables,
format/lint/types, production packaging and security. Factory 42247666690 and
legacy 42247666728 passed. Axe checked 184 isolated fixture states, plus
96 live staging and 64 live production states,
with zero WCAG-tagged violations. Incomplete results remain for human review.
Exact-runtime hosted session/customer and public-page checks exited 0 in both
environments, including mobile/desktop, themes, logout and persistence.

Local Docker WebKit retained a maximum-one-RGB-level difference in an exact dock
image comparison: the earlier full command had 171 passed/1 failed; the final
focused command had 9 passed/1 failed. Hosted exact header/full-suite gates passed
unchanged. A fresh-render diagnostic produced identical approved/current PNGs;
a longer control was inconclusive after a fixture-loading timeout. No assertions
were relaxed. The PR-triggered hosted workflow 42247666764 failed before deployment
because the expected runtime was not live; no account tests ran in that workflow.
It is not relabeled passed. Explicit post-deployment acceptance exited 0.

Manual screen-reader/physical-device testing, gradient/translucent contrast review,
third-party maps/payment/source documents and entitled production-owner journeys
remain unverified. Owner/admin flows were exercised with isolated fixtures;
hosted ordinary accounts were denied owner APIs. No legal certification or complete
WCAG conformance is claimed. See `app/docs/ACCESSIBILITY.md` for the manual checklist.
This documentation-only sign-off does not redeploy or relabel the observed runtimes.
The prior 0.23.1 release uses the same schema and is the compatible code rollback
candidate; no database reset or restore was performed.

### Command evidence

Commands are from `app/` unless noted. Final application CI ran the configured
commands in repository order. Passed means exit 0; local failures remain separate.

| Command | Result |
| --- | --- |
| `uv sync --frozen --dev`, `npm ci`, `uv lock --check` | Passed; locked axe dependency installed |
| `.venv/bin/ruff format --check landwolf tests scripts`, `npm run format:check` | Passed |
| `.venv/bin/ruff check landwolf tests scripts`, `npm run lint` | Passed |
| `.venv/bin/mypy landwolf`, `npm run typecheck` | Passed |
| `npm run test:unit` | Passed, 28 |
| `.venv/bin/pytest -q -m 'not browser'` | Passed, 782 |
| `.venv/bin/python scripts/check_postgres.py` | Passed in disposable CI PostgreSQL |
| `.venv/bin/python scripts/check_restore.py` | Passed, row digests across 49 tables |
| `npm run build` | Passed |
| `.venv/bin/pytest -q -m browser tests/test_commercial_browser.py` | Passed, 8 |
| `.venv/bin/pytest -q -m browser tests/test_public_pages_browser.py` | Passed, 6 |
| `.venv/bin/pytest -q -m browser tests/test_theme_browser.py` | Passed, 8 |
| `.venv/bin/pytest -q -m browser tests/test_source_list_browser.py` | Passed, 4 |
| `.venv/bin/pytest -q -m browser tests/test_mobile_research_browser.py tests/test_dock_browser.py tests/test_wolf_assistant_browser.py` | Passed, 18 |
| `.venv/bin/pytest -q -m browser` | Passed in final CI, 172; earlier local full run failed, 171 passed/1 failed |
| `.venv/bin/pytest -q -x -m browser tests/test_header_css_browser.py` | Passed in final hosted header job, 2 |
| Local combined `pytest -q -m browser tests/test_accessibility_browser.py tests/test_header_css_browser.py` | Failed overall, 9 passed/1 WebKit image comparison failed; all 8 accessibility cases passed |
| Supplementary `pytest -q -c pyproject.toml /manual/test_manual_accessibility.py` in the prepared browser container | Passed, 2 keyboard/reflow cases on final candidate; not a screen-reader test |
| `.venv/bin/python -m build`, `.venv/bin/python scripts/check_package.py` | Passed; final Hunt group markup verified inside wheel |
| `.venv/bin/bandit -r landwolf` | Passed, no findings |
| `.venv/bin/pip-audit --local --skip-editable` | Passed, no known vulnerabilities |
| `npm audit --audit-level=moderate`, `npm run secrets` | Passed |
| Legacy isolated `pytest -q` | Passed, 53 in legacy CI |
| Factory configured tests/type checks/audit | Passed, 36 tests in factory CI |
| `git diff --check`, `git status --short` | Passed, clean release candidate |
| Real screen-reader and physical-device checklist | Not run |

### Exact-runtime hosted commands

| Command | Result |
| --- | --- |
| `python scripts/check_hosted_staging.py --environment staging --commit f904d5e34a7a9b1a8b82e194403a8392a54e9294` | Passed |
| `python scripts/check_public_seo.py --environment staging` | Passed |
| `python /manual/check_hosted_accessibility.py --environment staging --commit f904d5e34a7a9b1a8b82e194403a8392a54e9294` | Passed, 96 states/0 violations |
| `python scripts/check_hosted_staging.py --environment production --commit 18b53c81a3a3a662b9dbd7eb1681dbd3b9ba1718` | Passed |
| `python scripts/check_public_seo.py --environment production` | Passed |
| `python /manual/check_hosted_accessibility.py --environment production --commit 18b53c81a3a3a662b9dbd7eb1681dbd3b9ba1718` | Passed, 64 states/0 violations |

Hosted scripts ran in a prepared Chromium/WebKit container using the final locked
environment. Version, environment, commit and asset hashes were checked. Staging
payments remained disabled; production live-payment mode remained enabled. No
checkout, charge, entitlement grant or destructive customer operation was performed.
