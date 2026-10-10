#!/bin/sh
# Only the isolated staging container migrates its database during startup.
set -eu
if [ "${LANDWOLF_ENVIRONMENT:-}" != "staging" ]; then
    printf '%s\n' 'This entry point requires LANDWOLF_ENVIRONMENT=staging.' >&2
    exit 64
fi
python -m landwolf.cli init-db
exec python -m landwolf.serve
