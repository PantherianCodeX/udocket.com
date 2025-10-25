#!/usr/bin/env bash
set -euo pipefail
mkdir -p docs/build/pdf
if [ -f docs/src/tdd/TDD.md ]; then
  pandoc docs/src/tdd/TDD.md \
    --from gfm --to pdf \
    --output docs/build/pdf/tdd.pdf \
    --toc --toc-depth=3 --number-sections \
    --resource-path=docs/src:docs/build/mermaid \
    --metadata title="uDocket TDD" \
    --css docs/src/assets/css/print.css
else
  echo "TDD.md not found; skipping PDF build" >&2
fi

