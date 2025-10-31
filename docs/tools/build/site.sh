#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../../.. && pwd)"
PY="${PYTHON:-python3}"

cd "$ROOT_DIR"

echo "Generating runbook catalog..."
"$PY" -m docs.tools.build.runbook_catalog

echo "Generating diagrams index..."
"$PY" -m docs.tools.build.diagram_index

mkdocs -f docs/config/mkdocs.yml build --clean
