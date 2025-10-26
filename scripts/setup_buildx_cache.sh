#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.docker/buildx-cache}"
SUBDIRS=(
  dev
  platform
  platform_worker
  platform_beat
  keycloak
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
  mkdir -p "${ROOT}/${dir}/blobs/sha256" "${ROOT}/${dir}/ingest"
  if [ ! -f "${ROOT}/${dir}/index.json" ]; then
    printf '{"schemaVersion":2,"mediaType":"application/vnd.oci.image.index.v1+json","manifests":[]}\n' > "${ROOT}/${dir}/index.json"
  fi
  if [ ! -f "${ROOT}/${dir}/oci-layout" ]; then
    printf '{"imageLayoutVersion":"1.0.0"}\n' > "${ROOT}/${dir}/oci-layout"
  fi
done

chmod -R 0777 "$ROOT"
