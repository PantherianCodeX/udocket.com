#!/usr/bin/env python3
"""Synchronise document control tables with front matter values."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Iterable, Iterator, List, Mapping, Sequence

from doc_tools.config.header_includes import (
    COMPUTED_FRONT_PLACEHOLDERS,
    DEFAULT_BUILTIN_HTML,
    HEADER_INCLUDES_CONFIG,
)
from doc_tools.config import paths
from doc_tools.common.doc_utils import (
    DOCUMENT_CONTROL_OPTIONAL_FIELDS,
    begin_auto_generated_marker,
    build_document_control_map,
    end_auto_generated_marker,
    parse_front_matter,
    stringify,
    yaml,
)

PROJECT_ROOT = paths.REPO_ROOT
OPTIONAL_FIELDS = DOCUMENT_CONTROL_OPTIONAL_FIELDS
DEFAULT_ROOTS: tuple[Path, ...] = (paths.DOCS_ROOT,)
MARKER_LABEL = "document-controls"
MARKER_BEGIN = begin_auto_generated_marker(MARKER_LABEL)
MARKER_END = end_auto_generated_marker(MARKER_LABEL)
PAGE_COUNT_HTML = DEFAULT_BUILTIN_HTML["page_count"]
PAGE_NUMBER_HTML = DEFAULT_BUILTIN_HTML["page_number"]
HEADER_CONFIG = HEADER_INCLUDES_CONFIG

@dataclass(frozen=True)
class HeaderUpdatePlan:
    start: int
    end: int
    replacement: List[str]


def _front_matter_bounds(lines: Sequence[str]) -> tuple[int, int] | None:
    if not lines or lines[0].strip() != "---":
        return None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return 1, idx
    return None


def _scan_block_end(lines: Sequence[str], idx: int, limit: int) -> int:
    cursor = idx
    while cursor < limit:
        line = lines[cursor]
        stripped = line.strip()
        if stripped and not line.startswith((" ", "\t")):
            return cursor
        cursor += 1
    return limit


def _find_header_block_range(lines: Sequence[str], bounds: tuple[int, int]) -> tuple[int, int]:
    start, end = bounds
    for idx in range(start, end):
        if lines[idx].strip().startswith("header-includes:"):
            block_end = _scan_block_end(lines, idx + 1, end)
            return idx, block_end
    return end, end


def _indent_literal_block(content: str) -> List[str]:
    lines = content.strip("\n").splitlines() or [""]
    indented = [f"    {line}" if line else "    " for line in lines]
    return ["  - |", *indented]


def _render_header_includes(front: Mapping[str, object]) -> List[str]:
    def _value(key: str) -> str:
        return escape(stringify(front.get(key, "")))

    front_context: dict[str, str] = {}
    for key in HEADER_CONFIG.front_matter_placeholders:
        if key in COMPUTED_FRONT_PLACEHOLDERS:
            continue
        front_context[key] = _value(key)

    for key in ("title", "subtitle", "classification", "last_updated"):
        if key not in front_context:
            front_context[key] = _value(key)

    subtitle = front_context.get("subtitle", "")
    if "subtitle_block" in HEADER_CONFIG.front_matter_placeholders:
        front_context["subtitle_block"] = f"{HEADER_CONFIG.subtitle_lead}{subtitle}" if subtitle else ""

    classification = front_context.get("classification", "")
    last_updated = front_context.get("last_updated", "")
    meta_parts = [
        part for part in (classification, f"Last updated {last_updated}" if last_updated else "") if part
    ]
    prefix = " · ".join(meta_parts)
    if prefix:
        prefix = f"{prefix} · "

    builtin_context = dict(DEFAULT_BUILTIN_HTML)
    builtin_context.setdefault("page_number", PAGE_NUMBER_HTML)
    builtin_context.setdefault("page_count", PAGE_COUNT_HTML)
    builtin_context["prefix"] = prefix

    blocks = HEADER_CONFIG.render(front_values=front_context, builtin_values=builtin_context)
    lines: List[str] = ["header-includes:"]
    for block in blocks:
        lines.extend(_indent_literal_block(block))
    return lines


def _plan_header_update(lines: List[str], front: Mapping[str, object]) -> HeaderUpdatePlan | None:
    bounds = _front_matter_bounds(lines)
    if bounds is None:
        return None
    block_start, block_end = _find_header_block_range(lines, bounds)
    replacement = _render_header_includes(front)
    existing = lines[block_start:block_end]
    if existing == replacement:
        return None
    return HeaderUpdatePlan(block_start, block_end, replacement)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update document controls from front matter")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=DEFAULT_ROOTS,
        help="Markdown files or directories to sync (defaults to platform/automation/data/etc.)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing files.")
    return parser.parse_args(argv)


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
                if not _has_document_controls(candidate):
                    continue
                resolved = candidate.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield resolved
        else:
            resolved = path.resolve()
            if resolved.name != "_template.md" and resolved not in seen and _has_document_controls(resolved):
                seen.add(resolved)
                yield resolved


def _has_document_controls(path: Path) -> bool:
    marker = "## document controls"
    try:
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                if raw_line.strip().lower() == marker:
                    return True
    except UnicodeDecodeError:
        return False
    return False


def sync_file(path: Path, *, dry_run: bool = False) -> bool:
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
    existing_map: dict[str, str] = {}
    for row in data_rows:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) >= 2:
            existing_map[cells[0]] = cells[1]

    combined_fields = build_document_control_map(front, include_additional=True)

    unexpected: list[str] = sorted(
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

    table_changed = markers_added or table_rows != new_rows
    header_plan = _plan_header_update(lines, front)

    if not table_changed and header_plan is None:
        return False

    if dry_run:
        print(f"[sync-document-controls] would update {path}")
        return True

    if table_changed:
        lines[table_start:table_start + len(table_rows)] = new_rows
    if header_plan is not None:
        lines[header_plan.start:header_plan.end] = header_plan.replacement

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[sync-document-controls] updated {path}")
    return True


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
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
            if sync_file(target, dry_run=args.dry_run):
                updated += 1
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[sync-document-controls] warning: failed to process {target}: {exc}", file=sys.stderr)

    if args.dry_run:
        print(f"[sync-document-controls] dry-run complete ({updated} file(s) would update)")
        return 0

    verify_cmd = [
        sys.executable,
        "-m",
        "doc_tools.check.structure",
        "--frontmatter",
        *[str(path) for path in targets],
    ]
    result = subprocess.run(verify_cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print("[sync-document-controls] verification via check_structure failed", file=sys.stderr)
        return result.returncode

    print(f"[sync-document-controls] completed ({updated} file(s) updated)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
