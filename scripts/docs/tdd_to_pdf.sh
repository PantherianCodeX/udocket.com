#!/usr/bin/env bash
set -euo pipefail
set -x  # trace commands so we know where it stops

# --- Find repo root ---
if ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; then :; else
  SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

DOCS="$ROOT/docs"
DIAGRAMS="$DOCS/diagrams"
OUT_DIR="$DIAGRAMS/_rendered"
BUILD="$DOCS/build"
CSS="$DOCS/pdf.css"
MD="$DOCS/TDD.md"
HTML="$BUILD/TDD.html"
PDF="$BUILD/TDD.pdf"

mkdir -p "$BUILD" "$OUT_DIR"

# echo "== Render Mermaid =="
# # Give mmdc a hard stop if it misbehaves (adjust 180s if needed)
# timeout 180s "$ROOT/scripts/docs/render_mermaid.sh" --verbose || {
#   echo "Mermaid render timed out or failed; check logs above." >&2
#   exit 1
# }

echo "== Pandoc → HTML =="
pandoc "$MD" \
  --from=gfm --to=html5 --standalone \
  --resource-path="$DOCS:$OUT_DIR" \
  --css "$CSS" \
  --highlight-style=pygments \
  -o "$HTML"

echo "== Puppeteer → PDF =="
# Also time-box the PDF step just in case
timeout 120s node "$ROOT/scripts/docs/html_to_pdf.mjs" \
  --in "$HTML" --out "$PDF" --size "Letter" --landscape || {
  echo "Puppeteer print timed out or failed; check logs above." >&2
  exit 1
}

echo "== Verify HTML assets =="
timeout 60s node "$ROOT/scripts/docs/verify_html_assets.mjs" \
  --in "$HTML" || {
  echo "Asset verification failed; check logs above." >&2
  exit 1
}

echo "✅ Wrote $PDF"
