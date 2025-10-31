#!/usr/bin/env bash
set -euo pipefail

# Unified Mermaid renderer
# - Scans docs/src by default and writes to docs/build/mermaid
# - Supports rendering all, changed, or specific paths
# - Uses mmdc (via MERMAID_CLI or npx fallback) with optional configs

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
SRC_ROOT="${MERMAID_SRC_ROOT:-$ROOT/docs/src}"
OUT_ROOT="${MERMAID_OUT_ROOT:-$ROOT/docs/build/mermaid}"
ASSET_ROOT="${MERMAID_ASSET_ROOT:-$ROOT/docs/src/.assets/mermaid}"
FORMAT="${MERMAID_FORMAT:-svg}"   # svg|png
CLI_BIN="${MERMAID_CLI:-}"
PUPPETEER_CONFIG="${MERMAID_PUPPETEER_CONFIG:-$ROOT/docs/config/puppeteer.config.json}"
CONFIG="${MERMAID_CONFIG:-$ROOT/docs/config/mermaid.config.json}"
POSTPROCESS="${MERMAID_POSTPROCESSOR:-$ROOT/docs/tools/postprocess_svg.py}"
DIFF_BASE="${MERMAID_DIFF_BASE:-origin/main}"

usage() {
  cat <<EOF
Usage: $(basename "$0") [--all] [--changed] [--paths <file1.mmd> [file2.mmd ...]] [--out-dir DIR] [--format svg|png] [--verbose]

Defaults:
  mode:       changed (use --all to rebuild everything)
  src root:   $SRC_ROOT
  out root:   $OUT_ROOT
  format:     $FORMAT
  diff base:  $DIFF_BASE
EOF
}

VERBOSE=0
MODE="changed"
declare -a PATHS

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all) MODE="all"; shift ;;
    --changed) MODE="changed"; shift ;;
    --paths) MODE="paths"; shift; while [[ $# -gt 0 && ! "$1" =~ ^-- ]]; do PATHS+=("$1"); shift; done ;;
    --out-dir) OUT_ROOT="$2"; shift 2 ;;
    --format) FORMAT="$2"; shift 2 ;;
    --verbose|-v) VERBOSE=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$CLI_BIN" ]]; then
  if command -v mmdc >/dev/null 2>&1; then
    CLI_BIN="mmdc"
  else
    CLI_BIN="npx --yes @mermaid-js/mermaid-cli"
  fi
fi

mkdir -p "$OUT_ROOT"

collect_all() {
  find "$SRC_ROOT" -type f -name '*.mmd' -not -path "$OUT_ROOT/*" -print0 | sort -z
}

collect_changed() {
  git -C "$ROOT" diff --name-only --diff-filter=ACMRTUXB "$DIFF_BASE" -- '*.mmd' -z 2>/dev/null || true
}

collect_paths() {
  if [[ ${#PATHS[@]} -eq 0 ]]; then return; fi
  printf '%s\0' "${PATHS[@]}"
}

render_one() {
  local input="$1"
  # Normalize to absolute
  if [[ ! "$input" = /* ]]; then input="$ROOT/$input"; fi
  # Compute path relative to SRC_ROOT
  local rel="${input#$SRC_ROOT/}"
  local dir="$(dirname "$rel")"
  local base="$(basename "$rel" .mmd)"
  local outdir="$OUT_ROOT/$dir"
  mkdir -p "$outdir"
  local out="$outdir/$base.$FORMAT"
  [[ $VERBOSE -eq 1 ]] && echo "Rendering ${rel} -> ${out#$ROOT/}"
  local args=(-i "$input" -o "$out")
  [[ -f "$PUPPETEER_CONFIG" ]] && args+=(-p "$PUPPETEER_CONFIG")
  [[ -f "$CONFIG" ]] && args+=(-c "$CONFIG")
  # shellcheck disable=SC2086
  if ! $CLI_BIN ${args[@]}; then
    echo "❌ Failed: $rel" >&2
    return 1
  fi
  if [[ "$FORMAT" == "svg" && -x "$POSTPROCESS" ]]; then
    python "$POSTPROCESS" "$out" || true
  fi
}

render() {
  local rc=0
  local rendered=0
  while IFS= read -r -d '' f; do
    # Skip non-existent files (e.g., deleted in diff)
    [[ -f "$f" ]] || continue
    if ! render_one "$f"; then rc=1; fi
    rendered=1
  done
  if [[ $rendered -eq 0 ]]; then
    echo "No Mermaid sources to render (mode=$MODE)"
  fi
  return $rc
}

case "$MODE" in
  all) collect_all | render ;;
  changed) collect_changed | render ;;
  paths) collect_paths | render ;;
esac

if [[ -n "$ASSET_ROOT" ]]; then
  rm -rf "$ASSET_ROOT"
  mkdir -p "$ASSET_ROOT"
  if ! cp -a "$OUT_ROOT/." "$ASSET_ROOT/" 2>/dev/null; then
    echo "warning: failed to mirror Mermaid artifacts into $ASSET_ROOT" >&2
  fi
fi
