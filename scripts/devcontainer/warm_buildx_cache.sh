#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGETS=(
  "platform:toolchain:0"
  "platform:python-deps:0"
  "platform-dev:toolchain:1"
  "platform-dev:python-deps:1"
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

BUILDER="${UDOCKET_BUILDX_BUILDER:-udocket-builder}"
export DOCKER_BUILDKIT=1

for entry in "${TARGETS[@]}"; do
  service="${entry%%:*}"
  rest="${entry#*:}"
  stage="${rest%%:*}"
  dev_tools="${rest##*:}"
  cache_dir="${ROOT}/.docker/buildx-cache/${service}"
  sentinel="${cache_dir}/.warm-${stage}"

  mkdir -p "$cache_dir"

  if [[ -f "$sentinel" ]]; then
    printf '[devcontainer] Build cache already warmed for %s; skipping.\n' "$service"
    continue
  fi

  printf '[devcontainer] Warming build cache for %s (%s stage)…\n' "$service" "$stage"
  if ! docker buildx build \
      --builder "$BUILDER" \
      --file "$ROOT/infra/docker/Dockerfile.platform" \
      --target "$stage" \
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
  printf '[devcontainer] Build cache warmed for %s (%s).\n' "$service" "$stage"
done

DOCS_CACHE_DIR="${ROOT}/.docker/buildx-cache/docs"
DOCS_SENTINEL="${DOCS_CACHE_DIR}/.warm-base"
mkdir -p "$DOCS_CACHE_DIR"

if [[ ! -f "$DOCS_SENTINEL" ]]; then
  printf '[devcontainer] Warming build cache for docs (base stage)…\n'
  if docker buildx build \
      --builder "$BUILDER" \
      --file "$ROOT/packages/docs_tooling/Dockerfile" \
      --target base \
      --cache-from "type=local,src=${DOCS_CACHE_DIR}" \
      --cache-to "type=local,dest=${DOCS_CACHE_DIR},mode=max" \
      --output=type=cacheonly \
      --progress=auto \
      "$ROOT"; then
    date > "$DOCS_SENTINEL"
    printf '[devcontainer] Build cache warmed for docs (base).\n'
  else
    printf '[devcontainer] Warning: build cache warm failed for docs; continuing without warmed cache.\n'
  fi
else
  printf '[devcontainer] Build cache already warmed for docs; skipping.\n'
fi
