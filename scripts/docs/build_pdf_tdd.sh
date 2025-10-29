#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
PY="${PYTHON:-python3}"

echo "Generating runbook catalog..."
"$PY" "$ROOT_DIR/scripts/docs/build_runbook_catalog.py"

echo "Generating diagrams index..."
"$PY" "$ROOT_DIR/scripts/docs/build_diagram_index.py"

mkdir -p docs/build/pdf
if [ -f docs/src/overview/tdd.md ]; then
  pandoc docs/src/overview/tdd.md \
    --from gfm --to pdf \
    --output docs/build/pdf/tdd.pdf \
    --toc --toc-depth=3 --number-sections \
    --resource-path=docs/src:docs/build/mermaid \
    --metadata title="uDocket TDD" \
    --css docs/src/assets/css/print.css
else
  echo "overview/tdd.md not found; skipping PDF build" >&2
fi
