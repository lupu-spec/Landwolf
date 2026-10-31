# LandWolf

LandWolf is the production application at [landwolf.ai](https://landwolf.ai/),
operated by L91 LLC. It provides authenticated property discovery, public-record
research, private decision research, Hunts, scenario analysis, CRM administration,
and an owner-only financial dashboard. Production uses live Stripe subscriptions
and preserves approved complimentary access and feedback-pilot policies.

## Start here

| Location | Purpose |
| --- | --- |
| [`app/`](app/README.md) | Current application, browser UI, tests and locked dependencies |
| [`render.yaml`](render.yaml) | Existing production service configuration; manual deployments |
| [`render.staging.yaml`](render.staging.yaml) | Existing isolated staging service configuration |
| [`RELEASES.md`](RELEASES.md) | Observed live versions and immutable deployment commits |
| [`app/docs/OWNER_FINANCE.md`](app/docs/OWNER_FINANCE.md) | Owner finances, expense imports and forecasting assumptions |
| [`app/docs/L91_LLC_CRM.md`](app/docs/L91_LLC_CRM.md) | Owner CRM operations |
| [`app/docs/HUNT.md`](app/docs/HUNT.md) | Hunt behavior and coverage limits |
| [`app/docs/DATA_SOURCE_VIEW.md`](app/docs/DATA_SOURCE_VIEW.md) | Compact source status list and freshness colors |
| [`app/docs/CODE_REVIEW_2026_10_16.md`](app/docs/CODE_REVIEW_2026_10_16.md) | Repository review, findings and refactoring evidence |
| [`app/docs/AI_CHANGE_GUIDE.md`](app/docs/AI_CHANGE_GUIDE.md) | How Codex/Chat should safely modify the application |
| [`app/docs/VERIFICATION.md`](app/docs/VERIFICATION.md) | Exact command results, resolved failures and remaining limits |
| [`archive/`](archive/README.md) | Retired application, old operational material and recovery index |

## Branches and releases

`main` is the production source; `staging` is the isolated verification source.
Work on short-lived `feature/` or `fix/` branches, open a pull request, and remove
those branches after merging. Preserve historical work in the dated recovery archive
rather than leaving dozens of completed engineering branches active.

A source branch head is not evidence of a running deployment. The October 11,
2026 maintenance baseline was v0.13.0 in production
(`3977a9aeced1dde09fb6d165726535b4ebc5aab1`) and staging
(`3a755fd3e1c65a82e1836c67d1cabca12a49f2f3`).
Automatic deployments and Blueprint synchronization are off. Consult
[RELEASES.md](RELEASES.md) and the live `/api/version` endpoint for the latest
confirmed production identity.

## Development

Use Python 3.12+, Node 24 and uv. From `app/`:

```sh
uv sync --frozen --dev
npm ci
npm run build
.venv/bin/python -m landwolf.cli init-db
.venv/bin/uvicorn landwolf.main:create_app --factory --host 127.0.0.1 --port 8000
```

Follow [the engineering policy](AGENTS.md) and [application gates](app/AGENTS.md).
Tests use isolated databases. Never apply restore tests or archived deployment tools
to the production database. Never commit credentials or customer exports.

See the [repository cleanup record](app/docs/REPOSITORY_CLEANUP.md) for the recovery
snapshot, source equivalence checks and configuration changes.
