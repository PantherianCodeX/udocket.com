#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

usage() {
  cat <<'USAGE'
Usage: codexhome.sh [OPTIONS] [PATH]

Set up the Codex CLI home directory for this workspace.

Arguments:
  PATH              Workspace directory. May be absolute or relative.
                    CODEX_HOME will be set to "<resolved PATH>/.codex".
                    Defaults to '.' (current working directory).

Options:
  --print-export    Print a shell export statement for use with eval/source.
  -h, --help        Show this help message.
USAGE
}

PRINT_EXPORT=false
POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --print-export)
      PRINT_EXPORT=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "[codexhome] Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done

if [[ ${#POSITIONAL[@]} -gt 1 ]]; then
  echo "[codexhome] Too many arguments." >&2
  usage >&2
  exit 1
fi

TARGET_PATH="${POSITIONAL[0]:-.}"

# Resolve workspace directory to absolute path (supports ~ expansion)
ABS_WORKSPACE=$(python3 -c "import os, sys; print(os.path.realpath(os.path.expanduser(sys.argv[1])))" "${TARGET_PATH}")

if [[ -z "${ABS_WORKSPACE}" ]]; then
  echo "[codexhome] Failed to resolve target path." >&2
  exit 1
fi

CODEX_HOME="${ABS_WORKSPACE}/.codex"
mkdir -p "${CODEX_HOME}"

# Persist choice for other tooling (ignored by git)
CODEX_META_DIR="${REPO_ROOT}/.codex"
mkdir -p "${CODEX_META_DIR}"
printf '%s\n' "${CODEX_HOME}" > "${CODEX_META_DIR}/.codexhome"

if ${PRINT_EXPORT}; then
  printf 'export CODEX_HOME="%s"\n' "${CODEX_HOME}"
  exit 0
fi

cat <<EOF
[codexhome] CODEX_HOME set to: ${CODEX_HOME}
[codexhome] To apply immediately in this shell run:
    eval "\$(scripts/codexhome.sh --print-export \"${TARGET_PATH}\")"
