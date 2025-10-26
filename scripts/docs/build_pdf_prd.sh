#!/usr/bin/env bash
set -euo pipefail
mkdir -p docs/build/pdf
if [ -f docs/src/prd/prd.md ]; then
  pandoc docs/src/prd/prd.md \
    --from gfm --to pdf \
    --output docs/build/pdf/prd.pdf \
    --toc --toc-depth=3 --number-sections \
    --resource-path=docs/src:docs/build/mermaid \
    --metadata title="uDocket PRD" \
    --css docs/src/assets/css/print.css
else
  echo "PRD not present; skipping PDF build" >&2
fi

