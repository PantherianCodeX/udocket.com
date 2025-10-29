#!/usr/bin/env python3
"""Shared helpers for documentation automation scripts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence
import re

try:
    import yaml
except ImportError:  # pragma: no cover - scripts warn upstream when yaml missing
    yaml = None

TITLE_CLEAN_REPLACEMENTS = [
    "Technical Design",
    "Technical Architecture",
    "Specification",
    "Overview",
]


def read_markdown_lines(path: Path) -> list[str]:
    """Return the contents of *path* as a list of lines."""

    return path.read_text(encoding="utf-8").splitlines()


def parse_front_matter(lines: Sequence[str]) -> dict[str, Any]:
    """Parse YAML front matter from *lines*."""

    if not lines or lines[0].strip() != "---":
        return {}
    if yaml is None:
        return {}

    collected: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        collected.append(line)
    if not collected:
        return {}
    try:
        data = yaml.safe_load("\n".join(collected)) or {}
    except Exception:
        raise
    if not isinstance(data, dict):
        return {}
    return data


def stringify(value: Any) -> str:
    """Normalise YAML values for table rendering."""

    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (bytes, bytearray)):
        return value.decode().strip()
    if isinstance(value, list):
        parts = [stringify(item) for item in value]
        return "; ".join(part for part in parts if part)
    if isinstance(value, dict):
        if yaml is not None:
            dumped = yaml.safe_dump(value, sort_keys=True).strip()
            return dumped.replace("\n", "; ")
        return str(value)
    return str(value).strip()


def derive_doc_label(title: str, *, fallback: str) -> str:
    """Return a concise document label suitable for cross references."""

    if not title:
        return fallback
    raw = title
    if "—" in raw:
        raw = raw.split("—", 1)[1]
    raw = raw.strip()
    baseline = re.sub(r"\s+", " ", raw).strip(" -–—")
    cleaned = raw
    for token in TITLE_CLEAN_REPLACEMENTS:
        cleaned = cleaned.replace(token, "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -–—")
    if not cleaned or cleaned.lower() in {"document"}:
        cleaned = baseline
    return cleaned or fallback
