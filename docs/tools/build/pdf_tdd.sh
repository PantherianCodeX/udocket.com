#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../../.. && pwd)"
PY="${PYTHON:-python3}"

cd "$ROOT_DIR"

echo "Generating runbook catalog..."
"$PY" -m docs.tools.build.runbook_catalog

echo "Generating diagrams index..."
"$PY" -m docs.tools.build.diagram_index

mkdir -p docs/build/pdf
if [ -f docs/src/overview/tdd.md ]; then
  pandoc docs/src/overview/tdd.md \
    --from gfm --to pdf \
    --output docs/build/pdf/tdd.pdf \
    --toc --toc-depth=3 --number-sections \
    --resource-path=docs/src:docs/build/mermaid \
    --metadata title="uDocket TDD" \
    --css docs/src/_assets/css/print.css
else
  echo "overview/tdd.md not found; skipping PDF build" >&2
fi
