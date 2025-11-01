#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGETS=(
  "platform:0"
  "platform-dev:1"
)

if [[ "${SKIP_BUILDX_WARM:-0}" == "1" ]]; then
  printf '[devcontainer] Build cache warm skipped (SKIP_BUILDX_WARM=1).\n'
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  printf '[devcontainer] Docker CLI unavailable; skipping build cache warm.\n'
  exit 0
fi

if ! docker info >/dev/null 2>&1; then
  printf '[devcontainer] Docker daemon unreachable; skipping build cache warm.\n'
  exit 0
fi

if ! docker buildx version >/dev/null 2>&1; then
  printf '[devcontainer] Docker Buildx not detected; skipping build cache warm.\n'
  exit 0
fi

if ! "$ROOT/scripts/devcontainer/ensure_buildx_builder.sh"; then
  printf '[devcontainer] Build cache warm skipped; unable to activate docker-container builder.\n'
  exit 0
fi

for entry in "${TARGETS[@]}"; do
  service="${entry%%:*}"
  dev_tools="${entry##*:}"
  cache_dir="${ROOT}/.docker/buildx-cache/${service}"
  sentinel="${cache_dir}/.warm-toolchain"

  mkdir -p "$cache_dir"

  if [[ -f "$sentinel" ]]; then
    printf '[devcontainer] Build cache already warmed for %s; skipping.\n' "$service"
    continue
  fi

  printf '[devcontainer] Warming build cache for %s (toolchain stage)…\n' "$service"
  if ! docker buildx build \
      --file "$ROOT/infra/docker/Dockerfile.platform" \
      --target toolchain \
      --build-arg DEV_TOOLS="$dev_tools" \
      --cache-from "type=local,src=${cache_dir}" \
      --cache-to "type=local,dest=${cache_dir},mode=max" \
      --output=type=cacheonly \
      --progress=auto \
      "$ROOT"; then
    printf '[devcontainer] Warning: build cache warm failed for %s; continuing without warmed cache.\n' "$service"
    continue
  fi

  date > "$sentinel"
  printf '[devcontainer] Build cache warmed for %s.\n' "$service"
done
