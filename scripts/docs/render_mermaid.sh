#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
DIAGRAM_DIR="$ROOT/docs/diagrams"
OUT_DIR="${MERMAID_OUTPUT_DIR:-$DIAGRAM_DIR/_rendered}"
CLI="${MERMAID_CLI:-mmdc}"
PUPPETEER_CONFIG="${MERMAID_PUPPETEER_CONFIG:-$ROOT/scripts/docs/puppeteer.config.json}"
CONFIG="${MERMAID_CONFIG:-$ROOT/scripts/docs/mermaid.config.json}"
POSTPROCESS="${MERMAID_POSTPROCESSOR:-$ROOT/scripts/docs/postprocess_svg.py}"

if ! command -v "$CLI" >/dev/null 2>&1; then
  echo "Mermaid CLI ($CLI) not found. Install @mermaid-js/mermaid-cli and ensure 'mmdc' is on PATH." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

shopt -s nullglob
shopt -s dotglob
rendered_any=0
failed=()
while IFS= read -r -d '' input; do
  rel_path="${input#$DIAGRAM_DIR/}"
  rel_dir="$(dirname "$rel_path")"
  rel_dir="${rel_dir#.}"  # strip leading ./ when basename
  filename="$(basename "$input" .mmd)"
  output_dir="$OUT_DIR"
  if [[ -n "$rel_dir" && "$rel_dir" != "." ]]; then
    output_dir="$OUT_DIR/$rel_dir"
    mkdir -p "$output_dir"
  fi
  svg_output="$output_dir/$filename.svg"
  echo "Rendering $rel_path -> ${svg_output#$ROOT/}"
  args=(-i "$input" -o "$svg_output" -p "$PUPPETEER_CONFIG")
  if [[ -f "$CONFIG" ]]; then
    args+=(-c "$CONFIG")
  fi
  if ! "$CLI" "${args[@]}"; then
    echo "❌ Failed to render $rel_path" >&2
    failed+=("$rel_path")
    continue
  fi
  if [[ -x "$POSTPROCESS" ]]; then
    python "$POSTPROCESS" "$svg_output" || true
  fi
  rendered_any=1
done < <(find "$DIAGRAM_DIR" -type f -name '*.mmd' ! -path "$OUT_DIR/*" -print0 | sort -z)

if [[ "$rendered_any" -eq 0 ]]; then
  echo "No Mermaid sources found under $DIAGRAM_DIR"
elif [[ "${#failed[@]}" -gt 0 ]]; then
  echo "⚠️ Completed with ${#failed[@]} failure(s):" >&2
  printf '  - %s\n' "${failed[@]}" >&2
  exit 1
else
  echo "Rendered diagrams into $OUT_DIR"
fi
