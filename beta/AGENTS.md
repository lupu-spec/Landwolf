# LandWolf rebuilt application instructions

The root engineering policy applies. This is the rebuilt free application. Keep its
runtime, accounts, database, and dependency environment separate from the legacy
application. Preserve the supplied LandWolf logo and navy/white visual identity.
Every property search, source, detail, save, analysis, and research route requires server
authentication. Payments stay disabled. Never use fabricated runtime listings,
unverified parcel coordinates, asking prices as valuations, or unknown costs as zero.
Production uses `landwolf.ai` with `www.landwolf.ai` redirected at Render. Preserve
the existing rebuilt service/database during promotion; do not reset accounts.
Configure explicit HTTPS origins; never derive trust from client forwarding headers.

Run commands from `beta/` using Python 3.12+ and Node 24. Install dependencies with
`uv sync --frozen --dev` and `npm ci`. Browser setup is
`.venv/bin/playwright install --with-deps chromium`.

Required gates, in order:

1. `.venv/bin/ruff format --check landwolf tests scripts`
   and `npm run format:check`.
2. `.venv/bin/ruff check landwolf tests scripts` and `npm run lint`.
3. `.venv/bin/mypy landwolf` and `npm run typecheck`.
4. `.venv/bin/pytest -q -m 'not browser'` (isolated API, parser, and invariant tests).
   CI must also run `.venv/bin/python scripts/check_postgres.py` with the disposable
   `landwolf_ci` PostgreSQL service. Never point this check at a production database.
5. `npm run build`, then `.venv/bin/pytest -q -m browser` for real browser flows.
6. `.venv/bin/python -m build` and `.venv/bin/python scripts/check_package.py`.
7. `.venv/bin/bandit -r landwolf`, `.venv/bin/pip-audit --local --skip-editable`,
   `npm audit --audit-level=moderate`, and `npm run secrets` (masked findings).
8. `git diff --check` and `git status --short` from the repository root.

`uv lock --check` and `npm ci` must also succeed after dependency edits.
Run the legacy `pytest -q` separately with the root requirements environment.
Do not combine the two dependency environments or change legacy billing tests.
Run live source verification explicitly with `.venv/bin/python -m landwolf.cli sync`;
fixture tests cannot establish current upstream availability. A deployment needs
its own database, HTTPS/browser checks, and an observed health check.
After public research adapter edits, also run
`.venv/bin/python -m landwolf.cli check-research` and
`.venv/bin/python -m landwolf.cli check-research --latitude 35.7804 --longitude -78.6391`.
These sample locations test upstream availability; they do not prove nationwide
coverage. Keep public reference records separate from listings and deal inputs.
Never treat approximate geocodes as parcel coordinates or missing flood data as low risk.

Preserve command exit statuses. Never describe missing tools, timeouts, skipped
tests, failed commands, an unbuilt container, or an unobserved deployment as passed.
Summarize results in `docs/VERIFICATION.md`; retain limitations and resolved failures.
