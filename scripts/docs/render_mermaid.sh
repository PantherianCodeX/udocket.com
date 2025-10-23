#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
DIAGRAM_DIR="$ROOT/docs/diagrams"
OUT_DIR="${MERMAID_OUTPUT_DIR:-$DIAGRAM_DIR/_rendered}"
CLI="${MERMAID_CLI:-mmdc}"
PUPPETEER_CONFIG="${MERMAID_PUPPETEER_CONFIG:-$ROOT/scripts/docs/puppeteer.config.json}"
CONFIG="${MERMAID_CONFIG:-$ROOT/scripts/docs/mermaid.config.json}"

postprocess_er_labels() {
  local svg_path="$1"
  python - <<'PY' "$svg_path"
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

path = Path(sys.argv[1])
if not path.exists():
    raise SystemExit(0)

namespace = "http://www.w3.org/2000/svg"
ET.register_namespace("", namespace)
try:
    tree = ET.parse(path)
except ET.ParseError:
    raise SystemExit(0)
root = tree.getroot()
changed = False

def find_ns(element, tag):
    return element.find(f".//{{{namespace}}}{tag}")

for label in root.findall(f".//{{{namespace}}}g[@class='edgeLabel']"):
    rect = label.find(f".//{{{namespace}}}rect[@class='background']")
    text = label.find(f".//{{{namespace}}}text")
    if rect is None or text is None:
        continue
    try:
        rect_x = float(rect.get("x", "0"))
        rect_width = float(rect.get("width", "0"))
    except ValueError:
        continue
    center = rect_x + (rect_width / 2.0)
    text.set("text-anchor", "middle")
    text.set("x", f"{center}")
    # Direct child tspans represent lines; align them to the center
    for outer in list(text.findall(f"./{{{namespace}}}tspan")):
        outer.set("x", f"{center}")
        outer.attrib.pop("dx", None)
        # Inner tspans hold word chunks; let them flow relative to parent
        for inner in outer.findall(f".//{{{namespace}}}tspan"):
            inner.attrib.pop("x", None)
            inner.attrib.pop("dx", None)
    changed = True

if changed:
    tree.write(path, encoding="unicode")
PY
}

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
  postprocess_er_labels "$svg_output" || true
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
