#!/usr/bin/env python3
"""Ensure strict files include the ``# pyright: strict`` directive.

Reads ``docs/typing/automation_manifest.json`` and enforces that every
module or package marked strict includes the pragma. Directories are
walked recursively for ``.py`` files.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "docs" / "typing" / "automation_manifest.json"
STRICT_PRAGMA = "# pyright: strict"


def _collect_strict_paths() -> list[Path]:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    strict_entries = data.get("strictModules", [])
    paths: list[Path] = []
    for entry in strict_entries:
        path_val = entry.get("path")
        if not isinstance(path_val, str):
            continue
        paths.append((REPO_ROOT / path_val).resolve())
    return paths


def _iter_python_files(targets: Iterable[Path]) -> Iterable[Path]:
    for path in targets:
        if path.is_dir():
            for file in path.rglob("*.py"):
                if file.is_file():
                    yield file
        elif path.suffix == ".py" and path.is_file():
            yield path


def _ensure_pragma(module_path: Path, dry_run: bool) -> bool:
    contents = module_path.read_text(encoding="utf-8").splitlines()
    if any(line.strip() == STRICT_PRAGMA for line in contents[:5]):
        return False

    insert_index = 0
    for idx, line in enumerate(contents[:5]):
        if line.startswith("from __future__ import") or line.startswith("#!/") or line.strip() == "":
            insert_index = idx + 1
        else:
            break

    contents.insert(insert_index, STRICT_PRAGMA)
    if not dry_run:
        module_path.write_text("\n".join(contents) + "\n", encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print files missing the pragma without modifying them",
    )
    args = parser.parse_args()

    strict_entries = _collect_strict_paths()
    updated = []
    for module_path in _iter_python_files(strict_entries):
        if _ensure_pragma(module_path, args.dry_run):
            updated.append(module_path.relative_to(REPO_ROOT))

    if args.dry_run:
        for module in updated:
            print(module)
    elif updated:
        print("Updated", len(updated), "files")
    else:
        print("All strict files already include the pragma")


if __name__ == "__main__":
    main()
