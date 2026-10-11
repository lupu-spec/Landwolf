#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${1:-}"
if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
  echo "usage: scripts/release.sh <staging|production>" >&2
  exit 2
fi

echo "Running deployment preflight for ${ENVIRONMENT}..."
python scripts/deployment_preflight.py --environment "$ENVIRONMENT"

echo "Preflight passed. Release command may proceed."
echo "Integrate your platform-specific deploy command below this line."
