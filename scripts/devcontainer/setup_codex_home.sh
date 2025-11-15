#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# Default to the Codex CLI's standard path inside the devcontainer. The# devcontainer maps a named volume to /root/.codex to persist across rebuilds.
CODEX_HOME="${CODEX_HOME:-/root/.codex}"
PORT_BASE="${CODEX_PORT_BASE:-20000}"
PORT_SPAN="${CODEX_PORT_SPAN:-10000}"

mkdir -p "${CODEX_HOME}"

PORT="$(python3 - "$ROOT" "$PORT_BASE" "$PORT_SPAN" <<'PY'
import hashlib
import sys

root = sys.argv[1]
base = int(sys.argv[2])
span = int(sys.argv[3])
digest = hashlib.sha256(root.encode("utf-8")).digest()
value = int.from_bytes(digest[:8], "big") % span
print(base + value)
PY
)"

printf '%s\n' "${PORT}" > "${CODEX_HOME}/app-port"

CONFIG_FILE="${CODEX_HOME}/config.toml"
if [[ ! -f "${CONFIG_FILE}" ]]; then
  cat > "${CONFIG_FILE}" <<EOF
model = "gpt-5-codex"

[app_server]
port = ${PORT}
EOF
fi

printf '[codex-setup] CODEX_HOME=%s (port %s)\n' "${CODEX_HOME}" "${PORT}"
