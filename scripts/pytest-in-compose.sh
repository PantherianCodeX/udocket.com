#!/usr/bin/env bash
set -euo pipefail

# Run pytest inside the docker compose "platform" service, mapping host paths to /app.
# Also ensures Postgres and Redis are up for Django tests.

ROOT_DIR=$(pwd)
CONTAINER_WORKDIR="/app"
SERVICE="platform"

# Bring up required deps if not already running
docker compose up -d postgres redis >/dev/null 2>&1 || true

# Rewrite any absolute host paths in args to container paths under /app
NEW_ARGS=()
for arg in "$@"; do
  case "$arg" in
    $ROOT_DIR/*)
      NEW_ARGS+=("${arg/$ROOT_DIR/$CONTAINER_WORKDIR}")
      ;;
    ./*)
      # Make relative paths absolute to container workdir
      ABS="${arg#./}"
      NEW_ARGS+=("$CONTAINER_WORKDIR/$ABS")
      ;;
    *)
      NEW_ARGS+=("$arg")
      ;;
  esac
done

exec docker compose run --rm -w "$CONTAINER_WORKDIR" "$SERVICE" pytest "${NEW_ARGS[@]}"

