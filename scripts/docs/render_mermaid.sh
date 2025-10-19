#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
DIAGRAM_DIR="$ROOT/docs/diagrams"
OUT_DIR="${MERMAID_OUTPUT_DIR:-$DIAGRAM_DIR/_rendered}"
CLI="${MERMAID_CLI:-mmdc}"

if ! command -v "$CLI" >/dev/null 2>&1; then
  echo "Mermaid CLI ($CLI) not found. Install @mermaid-js/mermaid-cli and ensure 'mmdc' is on PATH." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

shopt -s nullglob
for input in "$DIAGRAM_DIR"/*.mmd; do
  filename="$(basename "$input" .mmd)"
  output="$OUT_DIR/$filename.svg"
  echo "Rendering $input -> $output"
  "$CLI" -i "$input" -o "$output"
done
echo "Rendered diagrams into $OUT_DIR"

