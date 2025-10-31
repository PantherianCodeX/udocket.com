#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

printf '[devcontainer] Preparing build cache scaffolding…\n'
./scripts/setup_buildx_cache.sh

printf '[devcontainer] Syncing platform environment (dev group)…\n'
pushd apps/platform >/dev/null
uv sync --frozen --group dev
printf '[devcontainer] Refreshing vendored stubs…\n'
uv run python ../scripts/typing/vendor_stubs.py
popd >/dev/null

printf '[devcontainer] Syncing docs toolbox environment…\n'
pushd packages/udocket_docs >/dev/null
uv sync --frozen --extra dev
popd >/dev/null

printf '[devcontainer] All tooling ready. Happy hacking! 🚀\n'
