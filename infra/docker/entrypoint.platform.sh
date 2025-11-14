#!/usr/bin/env bash
set -euo pipefail

# Ensure Django manage commands run before starting the target process.
# Retries keep startup resilient when Postgres isn't ready yet.

RETRIES=${STARTUP_DB_RETRIES:-3}
SLEEP_SECONDS=${STARTUP_DB_RETRY_DELAY:-3}

function run_manage_cmd() {
  local cmd="$1"
  shift || true
  echo "[entrypoint] Running: python manage.py ${cmd} $*"
  python manage.py "${cmd}" "$@"
}

function run_with_retries() {
  local attempt=1
  while true; do
    if python manage.py migrate; then
      echo "[entrypoint] Database migrations applied."
      return 0
    fi
    if [[ ${attempt} -ge ${RETRIES} ]]; then
      echo "[entrypoint] Failed to run migrations after ${attempt} attempts." >&2
      return 1
    fi
    attempt=$((attempt + 1))
    echo "[entrypoint] Migrate failed; retrying in ${SLEEP_SECONDS}s (attempt ${attempt}/${RETRIES})..."
    sleep "${SLEEP_SECONDS}"
  done
}

RUN_PLATFORM_MIGRATIONS=${RUN_PLATFORM_MIGRATIONS:-1}
RUN_PLATFORM_BOOTSTRAP=${RUN_PLATFORM_BOOTSTRAP:-1}

if [[ "${SKIP_PLATFORM_BOOTSTRAP:-0}" == "1" ]]; then
  RUN_PLATFORM_MIGRATIONS=0
  RUN_PLATFORM_BOOTSTRAP=0
fi

if [[ "${RUN_PLATFORM_MIGRATIONS}" == "1" ]]; then
  if ! run_with_retries; then
    echo "[entrypoint] Migrations did not succeed after ${RETRIES} attempts; aborting startup." >&2
    exit 1
  fi
fi

if [[ "${RUN_PLATFORM_BOOTSTRAP}" == "1" ]]; then
  run_manage_cmd enable_rls || true
  run_manage_cmd bootstrap_defaults || true
fi

echo "[entrypoint] Starting process: $*"
exec "$@"
