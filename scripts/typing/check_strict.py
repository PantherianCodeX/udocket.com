#!/usr/bin/env python3
"""Run pyright across all modules listed in the strict manifest."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_MANIFEST = Path("docs/typing/automation_manifest.json")


def _load_strict_paths(manifest_path: Path) -> list[str]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = data.get("strictModules", [])
    paths = []
    for entry in entries:
        path = entry.get("path")
        verified_at = entry.get("verifiedAt")
        if not path or not verified_at:
            continue
        paths.append(path)
    unique = sorted(dict.fromkeys(paths))
    return unique


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to automation manifest (JSON)",
    )
    parser.add_argument(
        "--prefix",
        action="append",
        help=(
            "Filter strict modules to those whose path starts with the given prefix. "
            "May be provided multiple times."
        ),
    )
    parser.add_argument(
        "pyright_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments passed directly to pyright",
    )
    args = parser.parse_args()

    manifest_path = args.manifest
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    paths = _load_strict_paths(manifest_path)
    if args.prefix:
        prefixes = tuple(args.prefix)
        paths = [path for path in paths if path.startswith(prefixes)]
    if not paths:
        print("No strict modules recorded in manifest.")
        return 0

    exit_code = 0
    for path in paths:
        pyright_cmd = ["pyright", path, *args.pyright_args]
        print(f"→ pyright {path}")
        result = subprocess.run(pyright_cmd, check=False)
        if result.returncode != 0:
            exit_code = result.returncode

        mypy_cmd = [sys.executable, "-m", "mypy", path]
        print(f"→ mypy {path}")
        result = subprocess.run(mypy_cmd, check=False)
        if result.returncode != 0:
            exit_code = result.returncode

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
