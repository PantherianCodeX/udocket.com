#!/usr/bin/env bash
set -euo pipefail

TARGET_BUILDER="${UDOCKET_BUILDX_BUILDER:-udocket-builder}"

if ! command -v docker >/dev/null 2>&1; then
  printf '[devcontainer] Docker CLI unavailable; cannot configure Buildx builder.\n' >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  printf '[devcontainer] Docker daemon unreachable; cannot configure Buildx builder.\n' >&2
  exit 1
fi

if ! docker buildx version >/dev/null 2>&1; then
  printf '[devcontainer] Docker Buildx not detected; install buildx plugin or update Docker.\n' >&2
  exit 1
fi

current_info="$(docker buildx inspect 2>/dev/null || true)"
current_driver="$(printf '%s\n' "$current_info" | awk -F': ' '/^Driver:/ {print $2; exit}' | tr -d '[:space:]')"

if [[ "$current_driver" == "docker-container" ]]; then
  exit 0
fi

if docker buildx inspect "$TARGET_BUILDER" >/dev/null 2>&1; then
  docker buildx use "$TARGET_BUILDER" >/dev/null 2>&1 || true
else
  docker buildx create --name "$TARGET_BUILDER" --driver docker-container >/dev/null 2>&1 || true
  docker buildx use "$TARGET_BUILDER" >/dev/null 2>&1 || true
fi

current_info="$(docker buildx inspect 2>/dev/null || true)"
current_driver="$(printf '%s\n' "$current_info" | awk -F': ' '/^Driver:/ {print $2; exit}' | tr -d '[:space:]')"

if [[ "$current_driver" != "docker-container" ]]; then
  printf '[devcontainer] Active builder still uses driver "%s"; cache exports remain disabled.\n' "${current_driver:-unknown}" >&2
  printf '  -> Run: docker buildx create --use --name %s --driver docker-container\n' "$TARGET_BUILDER" >&2
  printf '  -> Or set SKIP_BUILDX_WARM=1 to skip cache warm steps.\n' >&2
  exit 1
fi

exit 0
