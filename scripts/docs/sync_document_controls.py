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
from collections import OrderedDict
from typing import Dict, Iterable, Iterator, List, Tuple

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - optional dependency warning
    yaml = None  # type: ignore

FIELD_MAPPINGS: List[Tuple[str, str]] = [
    ("Authors", "author"),
    ("Version", "version"),
    ("Status", "status"),
    ("Classification", "classification"),
    ("Last updated", "last_updated"),
    ("Owners", "owners"),
    ("Reviewers", "reviewers"),
    ("Approvers", "approvers"),
]
OPTIONAL_FIELDS = {"Approved by", "Approved date"}
EXCLUDED_FRONT_MATTER_KEYS = {
    "title",
    "subtitle",
    "header-includes",
    "adr_index",
    "related_adrs",
}
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


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode().strip()
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "; ".join(_stringify(item) for item in value if _stringify(item))
    if isinstance(value, dict):
        if yaml is not None:
            dumped = yaml.safe_dump(value, sort_keys=True).strip()
            return dumped.replace("\n", "; ")
        return str(value)
    return str(value).strip()


def _base_fields(front_matter: Dict[str, object]) -> OrderedDict[str, str]:
    result: "OrderedDict[str, str]" = OrderedDict()
    for label, key in FIELD_MAPPINGS:
        result[label] = _stringify(front_matter.get(key, ""))
    result["Approved by"] = _stringify(front_matter.get("approved_by", ""))
    result["Approved date"] = _stringify(front_matter.get("approved_date", ""))
    return result


def _additional_fields(front_matter: Dict[str, object]) -> OrderedDict[str, str]:
    base_keys = {key for _, key in FIELD_MAPPINGS}
    base_keys.update({"approved_by", "approved_date"})
    additional: "OrderedDict[str, str]" = OrderedDict()
    for key, value in front_matter.items():
        if key in base_keys or key in EXCLUDED_FRONT_MATTER_KEYS:
            continue
        label = key.replace("_", " ").replace("-", " ").title()
        additional[label] = _stringify(value)
    return additional


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
    if len(table_rows) < 2:
        print(
            f"[sync-document-controls] warning: {path} has incomplete document controls table; skipping",
            file=sys.stderr,
        )
        return False

    _header_row, _separator_row = table_rows[:2]
    data_rows = table_rows[2:]
    existing_map = {}
    for row in data_rows:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) >= 2:
            existing_map[cells[0]] = cells[1]

    base_fields = _base_fields(front)
    additional_fields = _additional_fields(front)
    combined_fields: "OrderedDict[str, str]" = OrderedDict()
    combined_fields.update(base_fields)
    combined_fields.update(additional_fields)

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

    new_rows = ["| Field | Value |", "| ----- | ----- |"]
    for field, expected in combined_fields.items():
        value = expected if expected or field not in OPTIONAL_FIELDS else ""
        new_rows.append(f"| {field} | {value} |")

    if table_rows == new_rows:
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
