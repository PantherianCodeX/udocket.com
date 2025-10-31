#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../../.. && pwd)"
PY="${PYTHON:-python3}"

cd "$ROOT_DIR"
"$PY" packages/udocket_docs/tools/pdf_build.py --target prd "$@"
