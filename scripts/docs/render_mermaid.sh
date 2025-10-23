#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
DIAGRAM_DIR="$ROOT/docs/diagrams"
OUT_DIR="${MERMAID_OUTPUT_DIR:-$DIAGRAM_DIR/out}"
CLI="${MERMAID_CLI:-mmdc}"
PUPPETEER_CONFIG="${MERMAID_PUPPETEER_CONFIG:-$ROOT/scripts/docs/puppeteer.config.cjs}"
CONFIG="${MERMAID_CONFIG:-$ROOT/scripts/docs/mermaid.config.json}"

if ! command -v "$CLI" >/dev/null 2>&1; then
  echo "Mermaid CLI ($CLI) not found. Install @mermaid-js/mermaid-cli and ensure 'mmdc' is on PATH." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

shopt -s nullglob
for input in "$DIAGRAM_DIR"/*.mmd; do
  filename="$(basename "$input" .mmd)"
  svg_output="$OUT_DIR/$filename.svg"
  png_output="$OUT_DIR/$filename.png"
  echo "Rendering $input -> $svg_output"
  args=(-i "$input" -o "$svg_output" -p "$PUPPETEER_CONFIG")
  if [[ -f "$CONFIG" ]]; then
    args+=(-c "$CONFIG")
  fi
  "$CLI" "${args[@]}"

  echo "Rendering $input -> $png_output"
  png_args=(-i "$input" -o "$png_output" -p "$PUPPETEER_CONFIG" -e png -s 2)
  if [[ -f "$CONFIG" ]]; then
    png_args+=(-c "$CONFIG")
  fi
  "$CLI" "${png_args[@]}"
done
echo "Rendered diagrams into $OUT_DIR"
