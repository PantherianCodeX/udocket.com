#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../../.. && pwd)"
PY="${PYTHON:-python3}"
MKDOCS_CONFIG="packages/udocket_docs/mkdocs.yml"
SITE_DIR="packages/udocket_docs/site"

cd "$ROOT_DIR"

echo "Generating runbook catalog..."
"$PY" -m docs.tools.build.runbook_catalog

echo "Generating diagrams index..."
"$PY" -m docs.tools.build.diagram_index

uv run mkdocs build --config-file "$MKDOCS_CONFIG" --site-dir "$SITE_DIR" --clean
