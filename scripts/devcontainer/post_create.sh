#!/usr/bin/env bash
set -euo pipefail

: "${UV_LINK_MODE:=copy}"
export UV_LINK_MODE

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

printf '[devcontainer] Preparing build cache scaffolding…\n'
./scripts/setup_buildx_cache.sh

printf '[devcontainer] Priming platform build cache…\n'
./scripts/devcontainer/warm_buildx_cache.sh

printf '[devcontainer] Syncing platform environment (dev group)…\n'
pushd apps/platform >/dev/null
uv sync --frozen --group dev --no-install-project
VENV_PY="/opt/venv/bin/python"
printf '[devcontainer] Refreshing vendored stubs…\n'
HASH_DIR="$ROOT/.cache/devcontainer"
mkdir -p "$HASH_DIR"
HASH_FILE="$HASH_DIR/vendor_stubs.hash"
if [[ -f "$ROOT/scripts/typing/vendor_stubs.py" ]]; then
  if [[ -f "$ROOT/apps/platform/uv.lock" ]]; then
    CURRENT_HASH=$(sha256sum "$ROOT/scripts/typing/vendor_stubs.py" "$ROOT/apps/platform/uv.lock" | sha256sum | awk '{print $1}')
  else
    CURRENT_HASH=$(sha256sum "$ROOT/scripts/typing/vendor_stubs.py" | awk '{print $1}')
  fi
  if [[ -f "$HASH_FILE" && "$CURRENT_HASH" == "$(cat "$HASH_FILE")" ]]; then
    printf '[devcontainer] Vendored stubs unchanged; skipping.\n'
  else
    if [[ -x "$VENV_PY" ]]; then
      "$VENV_PY" "$ROOT/scripts/typing/vendor_stubs.py"
      echo "$CURRENT_HASH" > "$HASH_FILE"
    else
      printf '[devcontainer] Warning: platform venv python not found; skipping stub refresh.\n'
    fi
  fi
else
  printf '[devcontainer] Warning: vendor stubs script missing; skipping.\n'
fi
popd >/dev/null

printf '[devcontainer] Syncing docs toolbox environment…\n'
pushd packages/docs_tooling >/dev/null
uv sync --frozen --group dev
popd >/dev/null

printf '[devcontainer] Initializing Codex home and port…\n'
./scripts/devcontainer/setup_codex_home.sh

printf '[devcontainer] All tooling ready. Happy hacking! 🚀\n'
