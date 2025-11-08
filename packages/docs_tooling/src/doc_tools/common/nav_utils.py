"""Shared helpers for manipulating MkDocs navigation sections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class NavEntry:
    label: str
    target: str


def find_section(lines: Sequence[str], header: str) -> tuple[int, int]:
    """Locate the nav section delimited by ``header`` and return (start, end)."""

    start = -1
    header_stripped = header.strip()
    for idx, line in enumerate(lines):
        if line.strip() == header_stripped:
            start = idx
            break
    if start == -1:
        raise RuntimeError(f"Navigation section '{header}' not found")
    end = start + 1
    while end < len(lines):
        if lines[end].startswith("- "):
            break
        end += 1
    return start, end


def collect_entries(lines: Sequence[str], start: int, end: int) -> list[NavEntry]:
    """Return ``NavEntry`` objects found between ``start`` and ``end``."""

    entries: list[NavEntry] = []
    for idx in range(start + 1, end):
        stripped = lines[idx].strip()
        if not stripped.startswith("- "):
            continue
        if ":" not in stripped:
            continue
        label, target = stripped[2:].split(":", 1)
        entries.append(NavEntry(label=label.strip(), target=target.strip()))
    return entries


__all__ = ["NavEntry", "collect_entries", "find_section"]
