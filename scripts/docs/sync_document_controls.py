#!/usr/bin/env python3
"""Synchronise document control tables with front matter values.

This helper updates the `Document controls` table in each target Markdown file
so that the values mirror the YAML front matter (version, status, owners, etc.).
It is intended for use in developer tooling (e.g. pre-commit hooks) and exits
with status 0 even when it encounters recoverable issues, emitting warnings
instead of failing the commit.

Usage examples:
    python scripts/docs/sync_document_controls.py
    python scripts/docs/sync_document_controls.py docs/src/services/digital-signer.md
    python scripts/docs/sync_document_controls.py docs/src/services

The script rewrites files in place when updates are required.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, Iterable, Iterator, List

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - optional dependency warning
    yaml = None  # type: ignore

DOCUMENT_CONTROLS_FIELDS = (
    "Authors",
    "Version",
    "Status",
    "Classification",
    "Last updated",
    "Owners",
    "Reviewers",
    "Approvers",
    "Approved by",
    "Approved date",
)
OPTIONAL_FIELDS = {"Approved by", "Approved date"}
DEFAULT_ROOT = Path("docs/src/services")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update document controls from front matter")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_ROOT],
        help="Markdown files or directories to sync (defaults to docs/src/services)",
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


def parse_front_matter(lines: List[str]) -> Dict[str, object]:
    if not lines or lines[0].strip() != "---" or yaml is None:
        return {}
    fm_lines: List[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)
    if not fm_lines:
        return {}
    try:
        data = yaml.safe_load("\n".join(fm_lines))
    except Exception as exc:  # pragma: no cover - hi-level warning only
        print(f"[sync-document-controls] warning: failed to parse front matter ({exc})", file=sys.stderr)
        return {}
    return data or {}


def format_field(field: str, front_matter: Dict[str, object]) -> str:
    if field == "Authors":
        authors = front_matter.get("author", []) or []
        if isinstance(authors, (str, bytes)):
            authors = [authors]
        return "; ".join(str(item).strip() for item in authors)
    if field == "Version":
        return str(front_matter.get("version", "")).strip()
    if field == "Status":
        return str(front_matter.get("status", "")).strip()
    if field == "Classification":
        return str(front_matter.get("classification", "")).strip()
    if field == "Last updated":
        return str(front_matter.get("last_updated", "")).strip()
    if field == "Owners":
        owners = front_matter.get("owners", []) or []
        return "; ".join(str(item).strip() for item in owners)
    if field == "Approvers":
        approvers = front_matter.get("approvers", []) or []
        return "; ".join(str(item).strip() for item in approvers)
    if field == "Reviewers":
        reviewers = front_matter.get("reviewers", []) or []
        return "; ".join(str(item).strip() for item in reviewers)
    return ""


def sync_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    front = parse_front_matter(lines)
    if not front:
        print(f"[sync-document-controls] warning: {path} missing usable front matter; skipping", file=sys.stderr)
        return False

    try:
        header_idx = next(i for i, line in enumerate(lines) if line.strip().lower() == "## Document Controls".lower())
    except StopIteration:
        print(f"[sync-document-controls] warning: {path} missing 'Document controls' section; skipping", file=sys.stderr)
        return False

    idx = header_idx + 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    table_start = idx
    table_rows: List[str] = []
    while idx < len(lines) and lines[idx].startswith("|"):
        table_rows.append(lines[idx])
        idx += 1
    if len(table_rows) < 3:
        print(f"[sync-document-controls] warning: {path} has incomplete document controls table; skipping", file=sys.stderr)
        return False

    header_row, separator_row, *data_rows = table_rows
    existing_map = {}
    for row in data_rows:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) >= 2:
            existing_map[cells[0]] = cells[1]

    new_rows = [header_row, separator_row]
    changed = False
    for field in DOCUMENT_CONTROLS_FIELDS:
        expected = format_field(field, front)
        if field in OPTIONAL_FIELDS and not expected:
            expected = existing_map.get(field, "")
        current = existing_map.get(field, "")
        if expected != current:
            changed = True
        new_rows.append(f"| {field} | {expected} |")

    if not changed and len(new_rows) == len(table_rows) and all(a == b for a, b in zip(new_rows, table_rows)):
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

    print(f"[sync-document-controls] completed ({updated} file(s) updated)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
