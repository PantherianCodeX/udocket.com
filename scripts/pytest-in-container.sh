#!/usr/bin/env bash
set -euo pipefail

# Ensure the platform service is running so we can exec into it.
docker compose up -d platform >/dev/null

# Forward pytest args (default to test discovery when none provided).
if [ $# -eq 0 ]; then
  docker compose exec -T platform pytest
else
  docker compose exec -T platform pytest "$@"
fi
