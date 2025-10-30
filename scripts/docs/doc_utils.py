#!/usr/bin/env python3
"""Shared helpers for documentation automation scripts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Sequence, Tuple
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

PREAMBLE_DIVIDER = "**|**"


def slugify(text: str) -> str:
    """Return a URL-safe slug derived from *text*."""

    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return slug.strip("-")


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


def replace_marked_section(original: str, begin: str, end: str, replacement: str) -> str:
    """Replace the content enclosed by *begin* and *end* markers in *original*."""

    if begin not in original or end not in original:
        raise RuntimeError(f"Expected markers '{begin}' and '{end}' to be present")

    before, remainder = original.split(begin, 1)
    _, after = remainder.split(end, 1)
    body = replacement.strip()
    return f"{before}{begin}\n{body}\n{end}{after}"


# ---------------------------------------------------------------------------
# Key/name helpers shared across documentation tooling
# ---------------------------------------------------------------------------


def normalize_key(value: str) -> str:
    """Normalise *value* to a lowercase ``snake_case`` token."""

    tokens = re.findall(r"[a-z0-9]+", value.lower())
    return "_".join(token for token in tokens if token)


def key_variants(raw_key: str) -> Tuple[str, ...]:
    """Return normalised key variants accounting for pluralisation."""

    base = normalize_key(raw_key)
    variants: list[str] = []
    if base:
        variants.append(base)
        if base.endswith("s") and not base.endswith("ss"):
            trimmed = base[:-1]
            if trimmed:
                variants.append(trimmed)
        elif not base.endswith("s"):
            variants.append(f"{base}s")
    # Preserve order while removing duplicates.
    return tuple(dict.fromkeys(variants))


def format_label(key: str) -> str:
    """Format *key* into a human readable label."""

    parts = re.split(r"[_\s-]+", key.strip())
    words: list[str] = []
    for index, part in enumerate(parts):
        if not part:
            continue
        lower = part.lower()
        if index > 0 and lower in {"and", "or", "the", "a", "an", "of", "in", "on", "for", "to", "with", "by"}:
            words.append(lower)
        else:
            words.append(part.capitalize())
    return " ".join(words) if words else key


# ---------------------------------------------------------------------------
# Markdown table helpers
# ---------------------------------------------------------------------------


def split_table_row(row: str) -> list[str]:
    """Return the individual cells for a markdown table *row*."""

    stripped = row.strip()
    if not stripped.startswith("|"):
        return []
    content = stripped.strip("|")
    return [cell.strip() for cell in content.split("|")]


def is_table_separator(line: str) -> bool:
    """Return ``True`` if *line* represents a markdown table separator row."""

    cells = split_table_row(line)
    if not cells:
        return False
    for cell in cells:
        normalized = cell.replace(" ", "")
        if not normalized:
            return False
        if not re.fullmatch(r":?-{3,}:?", normalized):
            return False
    return True


def normalize_table_cell(cell: str) -> str:
    """Return *cell* stripped of surrounding whitespace/markdown code fences."""

    value = cell.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1].strip()
    return value


def iter_markdown_tables(
    lines: Sequence[str],
    *,
    allow_optional_tags: bool = False,
) -> Iterable[Tuple[int, list[str]]]:
    """Yield ``(index, rows)`` for each markdown table present in *lines*.

    If ``allow_optional_tags`` is ``True`` the first cell may begin with
    ``[optional]`` (whitespace permitted before the tag). The returned rows
    preserve their original order and content.
    """

    idx = 0
    in_code_fence = False
    while idx < len(lines):
        raw_line = lines[idx]
        stripped = raw_line.strip()
        fence = stripped.startswith("```") or stripped.startswith("~~~")
        if fence:
            in_code_fence = not in_code_fence
            idx += 1
            continue
        if in_code_fence or not stripped.startswith("|"):
            idx += 1
            continue

        header_cells = split_table_row(stripped)
        if not header_cells:
            idx += 1
            continue

        # Skip blank lines to locate the separator.
        lookahead = idx + 1
        while lookahead < len(lines) and not lines[lookahead].strip():
            lookahead += 1
        if lookahead >= len(lines):
            break

        separator_candidate = lines[lookahead].strip()
        if not separator_candidate.startswith("|") or not is_table_separator(separator_candidate):
            idx += 1
            continue

        rows = [lines[idx], lines[lookahead]]
        row_idx = lookahead + 1
        while row_idx < len(lines):
            candidate_raw = lines[row_idx]
            candidate = candidate_raw.strip()
            if not candidate or not candidate.startswith("|"):
                break
            if is_table_separator(candidate):
                row_idx += 1
                continue
            rows.append(candidate_raw)
            row_idx += 1
        yield idx, rows
        idx = row_idx
