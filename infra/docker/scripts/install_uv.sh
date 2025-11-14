#!/usr/bin/env bash
set -euo pipefail

# Install uv into /usr/local/bin using a cached installer script.

cache_dir="/root/.cache/uv-installer"
mkdir -p "$cache_dir"
script="$cache_dir/install.sh"
if [ ! -f "$script" ]; then
  curl -fsSL https://astral.sh/uv/install.sh -o "$script"
fi
UV_INSTALL_DIR=/usr/local/bin sh "$script"
uv venv .venv --python python3.12 --cache-dir ".uv-cache"
