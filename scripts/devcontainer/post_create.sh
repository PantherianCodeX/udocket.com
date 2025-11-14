#!/usr/bin/env bash
set -euo pipefail

: "${UV_LINK_MODE:=copy}"
export UV_LINK_MODE

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

VENV_DIR="${UV_PROJECT_ENVIRONMENT:-$ROOT/.venv}"
export UV_PROJECT_ENVIRONMENT="$VENV_DIR"
export VIRTUAL_ENV="$VENV_DIR"
export PATH="$VENV_DIR/bin:${PATH}"

printf '[devcontainer] Preparing build cache scaffolding…\n'
"$ROOT/scripts/devcontainer/ensure_buildx_builder.sh"
export DOCKER_BUILDKIT=1
./scripts/setup_buildx_cache.sh

printf '[devcontainer] Priming platform build cache…\n'
./scripts/devcontainer/warm_buildx_cache.sh

printf '[devcontainer] Syncing platform environment (dev group)…\n'
pushd apps/platform >/dev/null
uv sync --frozen --group dev --no-install-project
VENV_PY="$VENV_DIR/bin/python"
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

PROFILE_SCRIPT="/etc/profile.d/udocket-venv.sh"
cat <<'EOF' > "$PROFILE_SCRIPT"
# shellcheck shell=sh
if [ -d /udocket/.venv/bin ]; then
  export VIRTUAL_ENV=/udocket/.venv
  export UV_PROJECT_ENVIRONMENT=/udocket/.venv
  case ":$PATH:" in
    *":/udocket/.venv/bin:"*) ;;
    *) PATH="/udocket/.venv/bin:${PATH}" ;;
  esac
  export PATH
fi
EOF
chmod 0644 "$PROFILE_SCRIPT"

printf '[devcontainer] Initializing Codex home and port…\n'
./scripts/devcontainer/setup_codex_home.sh

# Persist BuildKit defaults for interactive shells
cat <<'EOF' > /etc/profile.d/udocket-buildx.sh
# shellcheck shell=sh
export DOCKER_BUILDKIT=1
export UDOCKET_BUILDX_BUILDER=${UDOCKET_BUILDX_BUILDER:-udocket-builder}
EOF
chmod 0644 /etc/profile.d/udocket-buildx.sh

printf '[devcontainer] All tooling ready. Happy hacking! 🚀\n'
