#!/usr/bin/env python3
"""Shared helpers for documentation automation scripts."""

from __future__ import annotations

import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any, cast
from collections.abc import Iterable, Mapping, Sequence

import yaml

from packages.common.text import slugify as _slugify

TITLE_CLEAN_REPLACEMENTS = [
    "Technical Design",
    "Technical Architecture",
    "Specification",
    "Overview",
]

PREAMBLE_DIVIDER = "**|**"

DOCUMENT_CONTROL_FIELD_MAPPINGS: list[tuple[str, tuple[str, ...]]] = [
    ("Authors", ("authors", "author")),
    ("Version", ("version",)),
    ("Status", ("status",)),
    ("Classification", ("classification",)),
    ("Last updated", ("last_updated", "last-update")),
    ("Updated by", ("updated_by", "updated-by")),
    ("Owners", ("owners", "owner")),
    ("Reviewers", ("reviewers", "reviewer")),
    ("Approvers", ("approvers", "approver")),
    ("Approved by", ("approved_by", "approved-by")),
    ("Approved date", ("approved_date", "approved-at", "approved_at")),
]
DOCUMENT_CONTROL_OPTIONAL_FIELDS = {"Approved by", "Approved date"}
DOCUMENT_CONTROL_EXCLUDED_KEYS = {"title", "subtitle", "header-includes"}
DOCUMENT_CONTROL_ALIAS_KEYS = {
    alias for _, aliases in DOCUMENT_CONTROL_FIELD_MAPPINGS for alias in aliases
}

AUTO_GENERATED_PREFIX = "AUTO-GENERATED"
DEFAULT_AUTO_GENERATED_NOTE = "Managed automatically; do not edit manually."
MKDOCS_SLUG_RE = re.compile(r"[^\w\- ]+")


def slugify(value: str) -> str:
    """Return a URL-safe slug preserving ASCII characters."""

    return _slugify(value)


def mkdocs_slug(value: str) -> str:
    """Return the slug MkDocs/Material assigns to a heading."""

    lowered = value.strip().lower()
    cleaned = MKDOCS_SLUG_RE.sub("", lowered)
    collapsed = re.sub(r"\s+", "-", cleaned)
    slug = collapsed.strip("-")
    return slug or lowered or "section"


def begin_auto_generated_marker(label: str) -> str:
    """Return the standard BEGIN marker for an auto-generated block."""

    cleaned = label.strip()
    if not cleaned:
        raise ValueError("marker label must be non-empty")
    return f"<!-- BEGIN {AUTO_GENERATED_PREFIX}: {cleaned} -->"


def end_auto_generated_marker(label: str) -> str:
    """Return the standard END marker for an auto-generated block."""

    cleaned = label.strip()
    if not cleaned:
        raise ValueError("marker label must be non-empty")
    return f"<!-- END {AUTO_GENERATED_PREFIX}: {cleaned} -->"


def replace_auto_generated_section(original: str, label: str, replacement: str) -> str:
    """Replace the auto-generated section identified by *label* with *replacement*."""

    return replace_marked_section(
        original,
        begin_auto_generated_marker(label),
        end_auto_generated_marker(label),
        replacement,
    )


def _format_command(command: Sequence[str] | str) -> str:
    if isinstance(command, str):
        return command.strip()
    return " ".join(token.strip() for token in command if token.strip())


def auto_generated_comment(
    *,
    refresh_command: Sequence[str] | str | None = None,
    note: str | None = None,
) -> str:
    """Return a standard HTML comment for auto-generated sections."""

    if note:
        message = note.strip()
    elif refresh_command:
        command = _format_command(refresh_command)
        message = f"Run `{command}` to refresh."
    else:
        message = DEFAULT_AUTO_GENERATED_NOTE
    return f"<!-- {AUTO_GENERATED_PREFIX}: {message} -->"


def auto_generated_header(
    *,
    refresh_command: Sequence[str] | str | None = None,
    note: str | None = None,
) -> list[str]:
    """Return standard header lines (comment + blank line) for auto-generated blocks."""

    header = [auto_generated_comment(refresh_command=refresh_command, note=note)]
    header.append("")
    return header


def write_or_check(
    path: Path,
    content: str,
    *,
    check: bool,
    stale_message: str | None = None,
) -> bool:
    """Write *content* to *path* or verify it is current when ``check`` is ``True``.

    Returns ``True`` when up to date (or write succeeded). When ``check`` is ``True`` and the
    target differs, optionally prints *stale_message* to stderr and returns ``False``.
    """

    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if check:
        if existing is None or existing != content:
            if stale_message:
                print(stale_message, file=sys.stderr)
            return False
        return True

    if existing != content:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return True


def read_markdown_lines(path: Path) -> list[str]:
    """Return the contents of *path* as a list of lines."""

    return path.read_text(encoding="utf-8").splitlines()


def parse_front_matter(lines: Sequence[str]) -> dict[str, Any]:
    """Parse YAML front matter from *lines*."""

    if not lines or lines[0].strip() != "---":
        return {}

    collected: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        collected.append(line)
    if not collected:
        return {}
    try:
        raw: Any = yaml.safe_load("\n".join(collected))
    except Exception:
        raise
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        return {}
    return cast("dict[str, Any]", raw)


def stringify(value: Any) -> str:
    """Normalise YAML values for table rendering."""

    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (bytes, bytearray)):
        return value.decode().strip()
    if isinstance(value, list):
        parts = [stringify(item) for item in cast("list[Any]", value)]
        return "; ".join(part for part in parts if part)
    if isinstance(value, dict):
        dumped = yaml.safe_dump(value, sort_keys=True).strip()
        return dumped.replace("\n", "; ")
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


def _strip_heading_prefix(value: str, prefixes: Sequence[str] | None) -> str:
    if not prefixes:
        return value.strip()
    normalized = value.strip()
    for prefix in prefixes:
        pattern = re.compile(
            rf"^{re.escape(prefix)}(?:[-\s]*\d+)?\s*(?:[-—:]\s*)?(?P<body>.+)$",
            re.IGNORECASE,
        )
        match = pattern.match(normalized)
        if match:
            candidate = match.group("body").strip()
            if candidate:
                return candidate
    return normalized


def read_doc_label(
    path: Path,
    *,
    fallback: str | None = None,
    heading_prefixes: Sequence[str] | None = None,
) -> str:
    """Return a human-friendly label derived from front matter or first heading."""

    default_label = fallback or path.stem
    try:
        lines = read_markdown_lines(path)
    except OSError:
        return default_label

    front_matter = parse_front_matter(lines)
    if front_matter:
        candidate = stringify(front_matter.get("title", ""))
        if candidate:
            return derive_doc_label(candidate, fallback=default_label)

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            heading = _strip_heading_prefix(heading, heading_prefixes)
            if heading:
                return derive_doc_label(heading, fallback=default_label)
            break

    return default_label


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


def key_variants(raw_key: str) -> tuple[str, ...]:
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
        if index > 0 and lower in {
            "and",
            "or",
            "the",
            "a",
            "an",
            "of",
            "in",
            "on",
            "for",
            "to",
            "with",
            "by",
        }:
            words.append(lower)
        else:
            words.append(part.capitalize())
    return " ".join(words) if words else key


# ---------------------------------------------------------------------------
# Markdown table helpers
# ---------------------------------------------------------------------------


ESCAPABLE_MARKDOWN_CHARS = "\\`*_{}[]()#+-.!|"


def unescape_markdown(text: str) -> str:
    """Return *text* with standard Markdown backslash escapes removed."""

    result: list[str] = []
    idx = 0
    while idx < len(text):
        char = text[idx]
        if char == "\\" and idx + 1 < len(text) and text[idx + 1] in ESCAPABLE_MARKDOWN_CHARS:
            result.append(text[idx + 1])
            idx += 2
            continue
        result.append(char)
        idx += 1
    return "".join(result)


def split_table_row(row: str) -> list[str]:
    """Return the individual cells for a markdown table *row*."""

    stripped = row.strip()
    if not stripped.startswith("|"):
        return []
    cells: list[str] = []
    current: list[str] = []
    escape = False
    code_fence: int | None = None

    # Skip the leading pipe.
    for idx in range(1, len(stripped)):
        char = stripped[idx]
        if escape:
            current.append(char)
            escape = False
            continue
        if char == "\\":
            escape = True
            current.append(char)
            continue
        if char == "`":
            fence_len = 1
            while idx + fence_len < len(stripped) and stripped[idx + fence_len] == "`":
                fence_len += 1
            if code_fence is None:
                code_fence = fence_len
            elif fence_len == code_fence:
                code_fence = None
            current.extend("`" for _ in range(fence_len))
            idx += fence_len - 1
            continue
        if char == "|" and code_fence is None:
            cells.append("".join(current))
            current = []
            continue
        current.append(char)

    cells.append("".join(current))
    # Remove trailing empty cell caused by closing pipe.
    if cells and not cells[-1] and stripped.endswith("|"):
        cells.pop()
    # Normalise whitespace.
    return [cell.strip() for cell in cells]


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
    return unescape_markdown(value)


def _select_front_matter_value(front_matter: Mapping[str, Any], keys: Sequence[str]) -> str:
    for key in keys:
        if key in front_matter:
            return stringify(front_matter.get(key, ""))
    return ""


def build_document_control_map(
    front_matter: Mapping[str, Any],
    *,
    include_additional: bool = True,
) -> OrderedDict[str, str]:
    """Return an ordered mapping of document-control fields to values."""

    fields: OrderedDict[str, str] = OrderedDict()
    for label, keys in DOCUMENT_CONTROL_FIELD_MAPPINGS:
        fields[label] = _select_front_matter_value(front_matter, keys)

    if not include_additional:
        return fields

    for key, value in front_matter.items():
        if key in DOCUMENT_CONTROL_ALIAS_KEYS or key in DOCUMENT_CONTROL_EXCLUDED_KEYS:
            continue
        label = key.replace("_", " ").replace("-", " ").title()
        if label in fields:
            continue
        fields[label] = stringify(value)
    return fields


def iter_markdown_tables(
    lines: Sequence[str],
    *,
    allow_optional_tags: bool = False,
) -> Iterable[tuple[int, list[str]]]:
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


def parse_markdown_table(rows: Sequence[str]) -> list[dict[str, str]]:
    """Return a list of dictionaries representing the markdown *rows*."""

    if len(rows) < 2:
        return []
    header = split_table_row(rows[0])
    records: list[dict[str, str]] = []
    for raw in rows[2:]:
        cells = split_table_row(raw)
        if not cells:
            continue
        normalized = cells + [""] * max(0, len(header) - len(cells))
        record = {
            header[idx]: normalized[idx] if idx < len(normalized) else ""
            for idx in range(len(header))
        }
        records.append(record)
    return records


def iter_yaml_blocks(lines: Sequence[str]) -> Iterable[tuple[int, list[str]]]:
    """Yield ``(start_index, block_lines)`` for fenced YAML blocks within *lines*."""

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line.strip().startswith("```yaml"):
            start = idx + 1
            idx += 1
            block: list[str] = []
            while idx < len(lines) and not lines[idx].strip().startswith("```"):
                block.append(lines[idx])
                idx += 1
            yield start - 1, block
            while idx < len(lines) and not lines[idx].strip().startswith("```"):
                idx += 1
        idx += 1


def is_optional_yaml_value(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().lower()
    return normalized.startswith("[optional]") or normalized == "optional"


class YamlSchema:
    __slots__ = ("fields", "item", "kind", "optional")

    def __init__(
        self,
        kind: str,
        *,
        optional: bool = False,
        fields: Mapping[str, YamlSchema] | None = None,
        item: YamlSchema | None = None,
    ) -> None:
        self.kind = kind
        self.optional = optional
        self.fields = fields
        self.item = item


def build_yaml_schema(node: Any) -> YamlSchema:
    if isinstance(node, dict):
        mapping = cast("dict[str, Any]", node)
        fields: dict[str, YamlSchema] = {}
        for key, value in mapping.items():
            if is_optional_yaml_value(value):
                fields[key] = YamlSchema("any", optional=True)
                continue
            child = build_yaml_schema(value)
            fields[key] = child
        return YamlSchema("mapping", fields=fields)
    if isinstance(node, list):
        seq = cast("list[Any]", node)
        if not seq:
            return YamlSchema("sequence", item=YamlSchema("any"))
        if len(seq) == 1 and is_optional_yaml_value(seq[0]):
            return YamlSchema("sequence", optional=True, item=YamlSchema("any"))
        item_schema = build_yaml_schema(seq[0])
        return YamlSchema("sequence", item=item_schema)
    return YamlSchema("any")


def validate_yaml_schema(schema: YamlSchema, data: Any, path: list[str], errors: list[str]) -> None:
    if data is None:
        if not schema.optional:
            errors.append(f"{'.'.join(path) or '<root>'}: value missing")
        return
    if schema.kind == "mapping":
        if not isinstance(data, dict):
            errors.append(f"{'.'.join(path) or '<root>'}: expected mapping")
            return
        mapping = cast("dict[str, Any]", data)
        for key, child in (schema.fields or {}).items():
            value = mapping.get(key)
            if key not in data:
                if child.optional:
                    continue
                errors.append(f"{'.'.join(path + [key])}: missing key")
                continue
            validate_yaml_schema(child, value, path + [key], errors)
        return
    if schema.kind == "sequence":
        if not isinstance(data, list):
            errors.append(f"{'.'.join(path) or '<root>'}: expected list")
            return
        item_schema = schema.item or YamlSchema("any")
        sequence = cast("list[Any]", data)
        for index, item in enumerate(sequence):
            validate_yaml_schema(item_schema, item, path + [str(index)], errors)
        return
    # 'any' accepts any type
