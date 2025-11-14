"""Shared helper utilities for documentation checks."""

from __future__ import annotations

from collections.abc import Sequence

from doc_tools.common.doc_utils import split_table_row


def find_section_header(lines: Sequence[str], header: str) -> int:
    """Return the index of *header* within *lines* (case-insensitive)."""

    target = header.strip().lower()
    for idx, line in enumerate(lines):
        if line.strip().lower() == target:
            return idx
    raise ValueError(f"missing section header '{header}'")


def extract_table_rows(lines: Sequence[str], header_idx: int) -> list[str]:
    """Extract the contiguous markdown table rows following *header_idx*."""

    rows: list[str] = []
    idx = header_idx + 1
    capturing = False
    while idx < len(lines):
        raw = lines[idx]
        stripped = raw.strip()
        if not stripped:
            if capturing:
                break
            idx += 1
            continue
        if stripped.startswith("<!--"):
            if capturing:
                break
            idx += 1
            continue
        if not stripped.startswith("|"):
            if capturing:
                break
            idx += 1
            continue
        rows.append(stripped)
        capturing = True
        idx += 1
    return rows


def parse_table(rows: Sequence[str]) -> tuple[str, str, list[tuple[str, str]]]:
    """Parse *rows* into (header_row, separator_row, data_rows)."""

    if len(rows) < 2:
        raise ValueError("table requires at least header and separator rows")

    header_row = rows[0]
    separator_row = rows[1]
    data_rows: list[tuple[str, str]] = []
    for raw in rows[2:]:
        cells = split_table_row(raw)
        if len(cells) < 2:
            continue
        data_rows.append((cells[0], cells[1]))

    return header_row, separator_row, data_rows


__all__ = ["extract_table_rows", "find_section_header", "parse_table"]
