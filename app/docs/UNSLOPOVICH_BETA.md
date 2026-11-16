# Unslopovich beta candidate

Status: **NOT RELEASED**. No staging/production service or billing settings changed.

Changes: Explore uses a functional title and filter guidance; its search bar no
longer blurs the background; listing/search/map surfaces keep their silver theme
with smaller corners and no repeated shadows. Cards gain a visible keyboard-focus
outline. Header, dock, wolves, controls, account/billing logic and tests are unchanged.

Upstream method: https://github.com/erkamyaman/unslopovich/tree/883e82de54dfafc5df78b7129d0db3c148cdb13b
Scope/chart: `.unslopovich/chart.md`; diagnosis: `.unslopovich/visits/2026-11-15-2000-explore.md`.

## Local verification

Commands run from app using existing Node 24 and Python 3.12 environments.
Existing dependencies were reused; a fresh locked install was not possible because
external DNS/network access is unavailable. The baseline source tree was verified
identical to remote main before changes. Only app/web source changed.

| Command | Result | Exit |
| --- | --- | --- |
| `.venv/bin/ruff format --check landwolf tests scripts` | Passed | 0 |
| `npm run format:check` | Passed | 0 |
| `.venv/bin/ruff check landwolf tests scripts` | Passed | 0 |
| `npm run lint` | Passed | 0 |
| `.venv/bin/mypy landwolf` | Passed | 0 |
| `npm run typecheck` | Passed | 0 |
| `npm run test:unit` | Passed | 0 |
| `.venv/bin/pytest -q -m 'not browser'` | Failed | 124 |
| `npm run build` | Passed | 0 |
| `.venv/bin/pytest -q -x -m browser tests/test_theme_browser.py` | Failed | 1 |
| `.venv/bin/python -m build --no-isolation` | Failed | 1 |
| `.venv/bin/python -m build` | Failed: registry DNS | 1 |
| `.venv/bin/python scripts/check_package.py` | Failed | 1 |
| `.venv/bin/bandit -r landwolf` | Passed | 0 |
| `.venv/bin/pip-audit --local --skip-editable` | Failed | 1 |
| `npm audit --audit-level=moderate` | Failed | 1 |
| `npm run secrets` | Passed | 0 |
| `git diff --check` | Passed | 0 |

Frontend unit tests: 11 passed, zero failures/skips. Format check repeated and
passed after the final HTML wording correction. npm build included that correction.

Failed gates are not passes:
- API/non-browser pytest: 180-second timeout with no completed suite report.
- Browser theme test: local socket creation denied (Operation not permitted),
  before the browser journey. Remaining browser suites **Not run** for this blocker.
- Package build: setuptools build backend unavailable in reused environment;
  isolated build requires a network install. Package check found no wheel.
- Python/npm dependency audits: registry DNS unavailable, not vulnerability results.
- PostgreSQL integration, backup/restore, legacy suite, full hosted CI and deployed
  HTTPS/browser checks: **Not run**. No disposable database service available here.
- Performance: **Not profiled**. No candidate screenshots or cross-device visual
  approval were obtained; production observation is not candidate verification.

## Factory evidence

`l91 code` attempted the configured local Qwen endpoint and failed without applying
source. Read-only endpoint probe: operation not permitted. `l91 harness-run`
completed inspection then stopped at structure with FactoryError after two attempts.
`l91 security --repo app/web` passed with no findings or skipped-file warnings.
No local-AI generation or complete factory run is claimed.

## Resume and rollback

This is a review candidate, not a release version. Do not promote while gates are
incomplete. Run all app/AGENTS.md gates in a session that can reach the local AI,
start test servers, install locked dependencies and use disposable PostgreSQL.
Review both themes at 375/768/1280/1920 widths and 200% zoom, search/filter/list/map,
property details, keyboard focus and return navigation. Use Unslopovich's fresh
visual review after candidate screenshots exist. Assign a new beta version in the
runtime/package metadata only when preparing the deployable release, then deploy
the verified commit to isolated staging and record observed release/health evidence.
Production requires a separate promotion decision. No migration is involved.
The source-only candidate can be discarded by deleting its feature branch.

GitHub repository access works. The application workflow was observed enabled;
no credit/billing failure was observed. No hosted jobs or PR were started to preserve
the user's credit hold. This does not establish the account's billing balance.
