#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
PY="${PYTHON:-python3}"

echo "Generating runbook catalog..."
"$PY" "$ROOT_DIR/scripts/docs/build_runbook_catalog.py"

echo "Generating diagrams index..."
"$PY" "$ROOT_DIR/scripts/docs/build_diagram_index.py"

mkdocs -f docs/mkdocs.yml build --clean
