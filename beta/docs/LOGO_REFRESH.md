# Supplied LandWolf logo refresh — v0.10.3

The shared header on the login page and every app route now uses the exact
owner-supplied 1536 × 512 JPEG. Its new asset URL also avoids reusing the prior
cached PNG. The existing contain sizing preserves the full artwork on phones,
tablets and desktop. The compact LW favicon and Romulus/Remus illustrations
remain distinct interface assets. The no-photo-available artwork is unchanged.

Artwork SHA256: `e2306fabc89a4078ab8e58f613d63fbec69087108fc378d8436057b146b68fbf`.
Fallback SHA256: `ee886bf1a48cbaa82557f4c651adb0acee07afa6047567eda24af83644820a6c`.

## Verification

Passed locally (exit 0): `.venv/bin/ruff format --check landwolf tests scripts`;
`npm run format:check`; `.venv/bin/ruff check landwolf tests scripts`;
`npm run lint`; `.venv/bin/mypy landwolf`; `npm run typecheck`;
`npm run test:unit` (16); `.venv/bin/pytest -q -m 'not browser'` (512);
`npm run build`; `.venv/bin/python -m build`;
`.venv/bin/python scripts/check_package.py`; `.venv/bin/bandit -r landwolf`;
`.venv/bin/pip-audit --local --skip-editable`; `npm audit --audit-level=moderate`;
`npm run secrets`; `uv lock --check`; `git diff --cached --check`;
`git diff --check`; `git status --short`.

Initial package validation failed because local dist contained older releases;
cleaning ignored build outputs and rebuilding resolved it. No gate was weakened.
Local `.venv/bin/pytest -q -m browser -k supplied_header_logo` failed at launch:
Chromium and WebKit executables are unavailable. Hosted CI supplies those browsers
and the separate disposable PostgreSQL/restore gates. Physical devices are not
tested. No dependencies, billing, accounts, permissions or database changes.

Failed, unrelated: `LANDWOLF_DATABASE_URL=sqlite:////tmp/landwolf-logo-source-check.db LANDWOLF_AUTO_SYNC=false .venv/bin/python -m landwolf.cli sync`
exited 1 because Arkansas COSL returned HTTP 500. No production records were
altered by this disposable source check.

## Observed deployments

Staging: `536d83a2e74075aa85dcdd4438b6554e3bdc03d9`,
`dep-db4sis5ckfvc7383rs2g`, live 2026-10-10 05:14:29 UTC.
Its HTTPS version and exact uploaded asset hash were observed.

Full hosted gates passed: 512 backend, 16 frontend, 90 browser and 53 legacy
tests, PostgreSQL integration and exact-digest restore across 29 tables,
format/lint/types, build/package and all configured security gates.
Candidate gate run: https://github.com/lupu-spec/Landwolf/actions/runs/38026759469
Hosted staging: https://github.com/lupu-spec/Landwolf/actions/runs/38026759497

Six logo tests passed at 390, 820 and 1440 CSS pixels in Chromium and WebKit.
Screenshots were visually reviewed at phone, tablet and desktop widths.
PR #30 merged as `886906372f809c07277fb35b7f7f2cd2fddf85e9` with the identical
tested tree `6fda008392bb27819ca7c4a470a6e13549a20dde`.
Production: `886906372f809c07277fb35b7f7f2cd2fddf85e9`,
`dep-db4sogl9fdbs73ap63lg`, live 2026-10-10 05:26:16 UTC.
Hosted production HTTPS/browser checks passed:
https://github.com/lupu-spec/Landwolf/actions/runs/38027443790

Direct public-domain access from the local runner returned an intermediary page,
so public-domain verification uses hosted CI. The live smoke additionally checks
the exact uploaded logo and unchanged fallback hashes on both environments.
Physical devices were not tested.
