#!/usr/bin/env python3
"""Synchronise document control tables with front matter values.

This helper updates the `Document controls` table in each target Markdown file
so that the values mirror the YAML front matter (version, status, owners, etc.).
It is intended for use in developer tooling (e.g. pre-commit hooks) and exits
with status 0 even when it encounters recoverable issues, emitting warnings
instead of failing the commit.

Usage examples:
    python scripts/docs/sync_document_controls.py
    python scripts/docs/sync_document_controls.py docs/src/data/digital-signer.md
    python scripts/docs/sync_document_controls.py docs/src/platform docs/src/automation docs/src/data docs/src/customer

The script rewrites files in place when updates are required.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Iterator, List
import subprocess

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from scripts.docs.doc_roots import ALL_TEMPLATE_ROOTS  # noqa: E402
from scripts.docs.doc_utils import (  # noqa: E402
    DOCUMENT_CONTROL_OPTIONAL_FIELDS,
    build_document_control_map,
    parse_front_matter,
    yaml,
)

OPTIONAL_FIELDS = DOCUMENT_CONTROL_OPTIONAL_FIELDS
DEFAULT_ROOTS = [ROOT_DIR / root for root in ALL_TEMPLATE_ROOTS]
MARKER_BEGIN = "<!-- BEGIN AUTO-GENERATED: document-controls -->"
MARKER_END = "<!-- END AUTO-GENERATED: document-controls -->"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update document controls from front matter")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=DEFAULT_ROOTS,
        help="Markdown files or directories to sync (defaults to platform/automation/evidence/customer)",
    )
    return parser.parse_args()


def collect_targets(paths: Iterable[Path]) -> Iterator[Path]:
    seen: set[Path] = set()
    for path in paths:
        if not path.exists():
            print(f"[sync-document-controls] warning: {path} does not exist; skipping", file=sys.stderr)
            continue
        if path.is_dir():
            for candidate in sorted(path.rglob("*.md")):
                if candidate.name == "_template.md":
                    continue
                resolved = candidate.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield resolved
        else:
            resolved = path.resolve()
            if resolved.name != "_template.md" and resolved not in seen:
                seen.add(resolved)
                yield resolved


def sync_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    try:
        front = parse_front_matter(lines)
    except Exception as exc:  # pragma: no cover - hi-level warning only
        print(f"[sync-document-controls] warning: failed to parse front matter ({exc})", file=sys.stderr)
        return False
    if not front:
        print(f"[sync-document-controls] warning: {path} missing usable front matter; skipping", file=sys.stderr)
        return False

    try:
        header_idx = next(
            i for i, line in enumerate(lines) if line.strip().lower() == "## Document Controls".lower()
        )
    except StopIteration:
        print(f"[sync-document-controls] warning: {path} missing 'Document controls' section; skipping", file=sys.stderr)
        return False

    begin_idx = None
    end_idx = None
    markers_added = False
    for offset in range(header_idx + 1, len(lines)):
        stripped = lines[offset].strip()
        if not stripped:
            continue
        if stripped == MARKER_BEGIN:
            begin_idx = offset
            break
        if stripped.startswith("## "):
            break
        if stripped.startswith("|"):
            # no marker present; table starts here
            begin_idx = None
            break

    idx = header_idx + 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1

    if begin_idx is not None:
        table_start = begin_idx + 1
        try:
            end_idx = next(i for i in range(table_start, len(lines)) if lines[i].strip() == MARKER_END)
        except StopIteration:
            print(
                f"[sync-document-controls] warning: {path} missing '{MARKER_END}' after document controls table; skipping",
                file=sys.stderr,
            )
            return False
        table_rows = lines[table_start:end_idx]
    else:
        table_start = idx
        table_rows: List[str] = []
        while idx < len(lines) and lines[idx].startswith("|"):
            table_rows.append(lines[idx])
            idx += 1
        end_idx = table_start + len(table_rows)
        if table_rows:
            lines.insert(table_start, MARKER_BEGIN)
            lines.insert(end_idx + 1, MARKER_END)
            table_start += 1
            end_idx += 1
            markers_added = True
        else:
            print(
                f"[sync-document-controls] warning: {path} has incomplete document controls table; skipping",
                file=sys.stderr,
            )
            return False

    if len(table_rows) < 2:
        print(
            f"[sync-document-controls] warning: {path} has incomplete document controls table; skipping",
            file=sys.stderr,
        )
        return False

    data_rows = table_rows[2:]
    existing_map = {}
    for row in data_rows:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) >= 2:
            existing_map[cells[0]] = cells[1]

    combined_fields = build_document_control_map(front, include_additional=True)

    unexpected = sorted(
        field for field in existing_map if field not in combined_fields and field not in OPTIONAL_FIELDS
    )
    if unexpected:
        joined = ", ".join(unexpected)
        print(
            f"[sync-document-controls] warning: {path} document controls table has unexpected rows ({joined}); skipping",
            file=sys.stderr,
        )
        return False

    new_rows = ["| Field | Value |", "| --- | --- |"]
    for field, expected in combined_fields.items():
        value = expected if expected or field not in OPTIONAL_FIELDS else ""
        new_rows.append(f"| {field} | {value} |")

    if not markers_added and table_rows == new_rows:
        return False

    lines[table_start:table_start + len(table_rows)] = new_rows
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[sync-document-controls] updated {path}")
    return True


def main() -> int:
    args = parse_args()
    targets = list(collect_targets(args.paths))
    if not targets:
        print("[sync-document-controls] no markdown targets found", file=sys.stderr)
        return 0

    if yaml is None:
        print("[sync-document-controls] warning: PyYAML not available; cannot sync document controls", file=sys.stderr)
        return 0

    updated = 0
    for target in targets:
        try:
            if sync_file(target):
                updated += 1
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[sync-document-controls] warning: failed to process {target}: {exc}", file=sys.stderr)

    checker = ROOT_DIR / "scripts" / "docs" / "check_structure.py"
    verify_cmd = [sys.executable, str(checker), "--frontmatter", *[str(path) for path in targets]]
    result = subprocess.run(verify_cmd, cwd=str(ROOT_DIR))
    if result.returncode != 0:
        print("[sync-document-controls] verification via check_structure failed", file=sys.stderr)
        return result.returncode

    print(f"[sync-document-controls] completed ({updated} file(s) updated)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
