#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.docker/buildx-cache}"
SUBDIRS=(
  platform
  platform_worker
  platform_beat
  keycloak
  platform-dev
  docs
)

PARENT_DIR="$(dirname "$ROOT")"
if { [ -e "$PARENT_DIR" ] && [ ! -w "$PARENT_DIR" ]; } || { [ -d "$ROOT" ] && [ ! -w "$ROOT" ]; }; then
  if [ "$(id -u)" -ne 0 ]; then
    echo "Cannot modify ${ROOT}; rerun with sudo or from a root shell." >&2
    exit 1
  fi
fi

mkdir -p "$ROOT"

for dir in "${SUBDIRS[@]}"; do
  mkdir -p "${ROOT}/${dir}"
done

chmod -R 0777 "$ROOT"
