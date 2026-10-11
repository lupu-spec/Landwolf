# LandWolf historical material

`legacy/` contains the retired application, original configuration, deployment
instructions and inactive workflow definitions. Those files are historical records,
not deployment instructions for current production. The retained legacy regression
suite runs from this directory in its own Python environment.

All 38 original branch tips are listed in [BRANCHES.json](BRANCHES.json). The GitHub
branch [`archive/pre-cleanup-2026-10-11`](https://github.com/lupu-spec/Landwolf/tree/archive/pre-cleanup-2026-10-11)
points to archival commit `0067feb85c1ef8e60003b16a20cf5255b4d5acae`. Its 36 distinct
parents retain every original branch tip and its complete reachable history. This
is a recovery index, not a merge of those applications into production. Unmerged
private-seller work and marketing/branding assets are retained there.

The retired Render service is pinned to `archive/legacy-runtime-2026-10-11`, the
original main commit `5307de0a11fd75a7c51bdf5243f3e13179b95d38`, with automatic
deployment off. Its resources and data are retained.

Restore a recorded branch without changing production:

```sh
git fetch origin archive/pre-cleanup-2026-10-11
git switch -c restored/example <recorded-commit-sha>
```

Use the exact SHA from the index. Review old code independently before proposing any
new production change; archived trial/billing and deployment instructions can be
incompatible with the current application.
