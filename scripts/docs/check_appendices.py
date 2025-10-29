#!/usr/bin/env python3
"""Validate TDD appendices include synced front matter and document controls."""

from __future__ import annotations

import argparse
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Iterable, Iterator

try:
    import yaml
except ImportError:
    yaml = None

DEFAULT_ROOT = Path("docs/src/overview/tdd/appendices")
DOCUMENT_CONTROLS_HEADER = "## Document Controls"

FIELD_MAPPINGS = [
    ("Authors", "authors"),
    ("Version", "version"),
    ("Status", "status"),
    ("Classification", "classification"),
    ("Last updated", "last_updated"),
    ("Owners", "owners"),
    ("Reviewers", "reviewers"),
    ("Approvers", "approvers"),
]

OPTIONAL_FIELDS = {"Approved by", "Approved date"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate appendix front matter and controls")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_ROOT],
        help="Markdown files or directories to validate (defaults to TDD appendices)",
    )
    return parser.parse_args()


def collect_targets(paths: Iterable[Path]) -> Iterator[Path]:
    seen: set[Path] = set()
    for raw in paths:
        if not raw.exists():
            print(f"[check-appendices] warning: {raw} does not exist; skipping", file=sys.stderr)
            continue
        if raw.is_dir():
            for candidate in sorted(raw.rglob("*.md")):
                if candidate.name == "_template.md":
                    continue
                resolved = candidate.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield resolved
        else:
            resolved = raw.resolve()
            if resolved.name != "_template.md" and resolved not in seen:
                seen.add(resolved)
                yield resolved


def parse_front_matter(text: str) -> dict[str, object]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    if yaml is None:
        return {}
    fm_lines: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)
    if not fm_lines:
        return {}
    try:
        data = yaml.safe_load("\n".join(fm_lines))
    except Exception:
        return {}
    return data or {}


def stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        joined = "; ".join(stringify(item) for item in value if stringify(item))
        return joined
    if isinstance(value, dict):
        if yaml is not None:
            dumped = yaml.safe_dump(value, sort_keys=True).strip()
            return dumped.replace("\n", "; ")
        return str(value)
    return str(value).strip()


def expected_fields(front_matter: dict[str, object]) -> "OrderedDict[str, str]":
    base: "OrderedDict[str, str]" = OrderedDict()
    for label, key in FIELD_MAPPINGS:
        base[label] = stringify(front_matter.get(key, ""))
    base["Approved by"] = stringify(front_matter.get("approved_by", ""))
    base["Approved date"] = stringify(front_matter.get("approved_date", ""))
    return base


def locate_document_controls(lines: list[str]) -> tuple[int, list[str]] | None:
    try:
        header_idx = next(
            idx for idx, line in enumerate(lines) if line.strip().lower() == DOCUMENT_CONTROLS_HEADER.lower()
        )
    except StopIteration:
        return None

    idx = header_idx + 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    rows: list[str] = []
    while idx < len(lines) and lines[idx].startswith("|"):
        rows.append(lines[idx])
        idx += 1
    return header_idx, rows


def check_document(path: Path) -> list[str]:
    issues: list[str] = []
    text = path.read_text(encoding="utf-8")
    front_matter = parse_front_matter(text)
    lines = text.splitlines()

    if not front_matter:
        issues.append(f"{path}: missing or invalid front matter")
        return issues

    result = locate_document_controls(lines)
    if not result:
        issues.append(f"{path}: missing '{DOCUMENT_CONTROLS_HEADER}' section")
        return issues

    _, table_rows = result
    if len(table_rows) < 2:
        issues.append(f"{path}: document controls table incomplete")
        return issues

    header_row = table_rows[0]
    if "Field" not in header_row or "Value" not in header_row:
        issues.append(f"{path}: document controls table missing 'Field'/'Value' header")

    data_rows = table_rows[2:]  # skip header and separator
    values: dict[str, str] = {}
    for row in data_rows:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        field, value = cells[0], cells[1]
        values[field] = value

    expected = expected_fields(front_matter)
    for field, expected_value in expected.items():
        actual_value = values.get(field, "")
        if not actual_value and expected_value and field not in OPTIONAL_FIELDS:
            issues.append(f"{path}: document controls field '{field}' must not be empty")
        if expected_value and actual_value and actual_value != expected_value:
            issues.append(
                f"{path}: document controls field '{field}' value '{actual_value}' "
                f"does not match front matter '{expected_value}'"
            )
        if expected_value and field not in values:
            issues.append(f"{path}: document controls missing field '{field}'")
        if not expected_value and field not in OPTIONAL_FIELDS and actual_value:
            issues.append(
                f"{path}: document controls field '{field}' contains '{actual_value}' but front matter is blank"
            )

    for field in values:
        if field not in expected and field not in OPTIONAL_FIELDS:
            issues.append(f"{path}: document controls has unexpected field '{field}'")

    return issues


def main() -> int:
    args = parse_args()
    targets = list(collect_targets(args.paths))
    if not targets:
        print("[check-appendices] no markdown targets found", file=sys.stderr)
        return 1
    if yaml is None:
        print("[check-appendices] PyYAML is required to validate appendices", file=sys.stderr)
        return 1

    problems: list[str] = []
    for target in targets:
        problems.extend(check_document(target))

    if problems:
        for item in problems:
            print(item)
        return 1

    print("All appendices contain synced front matter and document controls.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

