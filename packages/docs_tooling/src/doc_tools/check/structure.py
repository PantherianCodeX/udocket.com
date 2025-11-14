#!/usr/bin/env python3
"""Validate documentation structure against the canonical template.

By default the checker inspects source documents under
``docs/`` and ensures:

* Numeric sections (``## 1``, ``### 3.1`` …) appear in the same order as 
  their accompanying ``_template.md`` file.
* Each section contains the preamble entries declared in the template, in the
  same order. Divider enforcement is shared with the Vale rule
  ``uDocket-Core.PreambleDivider``.
* No unexpected preamble entries are present.
* The "Document controls" table contains all required rows, values are present,
  **and** the values match the YAML front matter.

Typical usage (CLI/CI friendly):

    python -m doc_tools.check.structure
    python -m doc_tools.check.structure docs/experience/web-app.md
    python -m doc_tools.check.structure docs/platform docs/automation docs/data docs/customer docs/overview
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from collections.abc import Iterable, Iterator, Sequence

from doc_tools.config import paths
from doc_tools.check.requirements import (
    EXCLUDED_CONTROL_KEYS,
    OPTIONAL_KEYS,
    TEMPLATE_REQUIREMENTS,
)
from doc_tools.check.utils import extract_table_rows, find_section_header, parse_table
from doc_tools.common.doc_utils import (
    PREAMBLE_DIVIDER,
    YamlSchema,
    begin_auto_generated_marker,
    build_yaml_schema,
    end_auto_generated_marker,
    format_label,
    iter_markdown_tables,
    iter_yaml_blocks,
    key_variants,
    normalize_key,
    normalize_table_cell,
    parse_front_matter,
    split_table_row,
    stringify,
    validate_yaml_schema,
    yaml,
)

TEMPLATE_NAME = "_template.md"
HEADING_RE = re.compile(r"^(#{2,6})\s+(.*)")
PREAMBLE_RE = re.compile(r"^\*\*(.+?):\*\*\s*(.*)$")
DOCUMENT_CONTROLS_HEADER = "## Document Controls"
DOCUMENT_CONTROLS_LABEL = "document-controls"
DOCUMENT_CONTROLS_BEGIN = begin_auto_generated_marker(DOCUMENT_CONTROLS_LABEL)
DOCUMENT_CONTROLS_END = end_auto_generated_marker(DOCUMENT_CONTROLS_LABEL)
REQUIRED_FRONT_MATTER_KEYS = TEMPLATE_REQUIREMENTS.required_front_matter_keys

LOWERCASE_WORDS = {"and", "or", "the", "a", "an", "of", "in", "on", "for", "to", "with", "by"}
DISABLED_TEMPLATE_MESSAGES: set[Path] = set()


@dataclass(frozen=True)
class TableRowSpec:
    first_cell: str
    optional: bool


@dataclass(frozen=True)
class TableSpec:
    header: tuple[str, ...]
    rows: tuple[TableRowSpec, ...]


@dataclass(frozen=True)
class SectionSpec:
    numbering: tuple[int, ...]
    level: int
    title: str
    preamble_order: tuple[str, ...]
    preamble_requires_marker: dict[str, bool]
    tables: tuple[TableSpec, ...]
    yaml_schemas: tuple[YamlSchema, ...]
    required_markers: tuple[str, ...]


def build_front_matter_index(front_matter: dict[str, Any]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for key in front_matter:
        primary = normalize_key(key)
        variants = key_variants(key)
        if primary and primary not in variants:
            variants = (primary, *variants)
        for variant in variants:
            if not variant:
                continue
            index.setdefault(variant, []).append(key)
    return index


def template_disabled(template_path: Path) -> bool:
    content = template_path.read_text(encoding="utf-8")
    stripped = content.strip()
    if not stripped:
        return True
    if "template:disabled" in stripped.lower():
        return True
    return False


def extract_tables(
    lines: Sequence[str],
    start: int,
    end: int,
    *,
    allow_optional_tags: bool,
) -> list[TableSpec]:
    tables: list[TableSpec] = []
    segment = list(lines[start:end])
    for _, table_rows in iter_markdown_tables(segment, allow_optional_tags=allow_optional_tags):
        if len(table_rows) < 2:
            continue
        header_cells = split_table_row(table_rows[0])
        if not header_cells:
            continue
        data_rows: list[TableRowSpec] = []
        for raw_row in table_rows[2:]:
            cells = split_table_row(raw_row)
            if not cells:
                continue
            first_cell_raw = cells[0]
            optional = False
            if allow_optional_tags:
                stripped_first = first_cell_raw.lstrip()
                if stripped_first.lower().startswith("[optional]"):
                    optional = True
                    first_cell_raw = stripped_first[len("[optional]") :].strip()
            normalized_first = normalize_table_cell(first_cell_raw)
            data_rows.append(TableRowSpec(first_cell=normalized_first, optional=optional))
        tables.append(
            TableSpec(
                header=tuple(header_cells),
                rows=tuple(data_rows),
            ),
        )
    return tables


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate docs against the canonical template")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[paths.DOCS_ROOT],
        help="Markdown files or directories to validate (defaults to docs root)",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=None,
        help="Override `_template.md` path (defaults to nearest ancestor of first target)",
    )
    parser.add_argument(
        "--frontmatter",
        action="store_true",
        help="Only validate front matter and document controls",
    )
    return parser.parse_args()


def find_template(start: Path, override: Path | None) -> Path:
    if override:
        if not override.is_file():
            raise FileNotFoundError(f"Template override not found: {override}")
        return override.resolve()
    current = start if start.is_dir() else start.parent
    visited: set[Path] = set()
    while current not in visited:
        visited.add(current)
        candidate = current / TEMPLATE_NAME
        if candidate.is_file():
            return candidate.resolve()
        current = current.parent
    raise FileNotFoundError(f"Could not locate {TEMPLATE_NAME} starting from {start}")


def extract_numbering(title: str) -> tuple[int, ...] | None:
    title = title.strip()
    if m := re.match(r"^(\d+)\)", title):
        return (int(m.group(1)),)
    if m := re.match(r"^(\d+(?:\.\d+)+)", title):
        return tuple(int(part) for part in m.group(1).split("."))
    return None


def parse_sections(markdown: str) -> list[tuple[tuple[int, ...], int, str, int]]:
    sections: list[tuple[tuple[int, ...], int, str, int]] = []
    lines = markdown.splitlines()
    for idx, line in enumerate(lines, start=1):
        m = HEADING_RE.match(line)
        if not m:
            continue
        level = len(m.group(1))
        title = m.group(2).strip()
        numbering = extract_numbering(title)
        if numbering is None:
            continue
        sections.append((numbering, level, title, idx))
    return sections


def gather_preamble(lines: Sequence[str], start_idx: int) -> list[tuple[int, str, str]]:
    entries: list[tuple[int, str, str]] = []
    idx = start_idx
    while idx < len(lines):
        line = lines[idx]
        trimmed = line.rstrip()
        if not trimmed:
            idx += 1
            continue
        m = PREAMBLE_RE.match(trimmed)
        if not m:
            break
        label_raw, body = m.groups()
        label = label_raw.strip()
        entries.append((idx, label, body.rstrip()))
        idx += 1
    return entries


def build_template_spec(template_path: Path) -> list[SectionSpec]:
    content = template_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    specs: list[SectionSpec] = []
    sections = parse_sections(content)
    for index, (numbering, level, title, line_no) in enumerate(sections):
        preamble_entries = gather_preamble(lines, line_no)
        order = tuple(label for _, label, _ in preamble_entries)
        marker_map: dict[str, bool] = {}
        for _, label, body in preamble_entries:
            cleaned = body.rstrip()
            has_divider = cleaned.endswith(PREAMBLE_DIVIDER)
            marker_map[label] = has_divider
        start_idx = line_no - 1
        next_idx = len(lines)
        for _, candidate_level, _, candidate_line in sections[index + 1 :]: # candidate_numbering replaced with _ (not used)
            if candidate_level <= level:
                next_idx = candidate_line - 1
                break
        content_start = start_idx + 1
        content_end = next_idx if next_idx >= 0 else len(lines)
        if content_end <= content_start:
            content_end = len(lines)
        segment_lines = lines[max(content_start, 0) : min(content_end, len(lines))]
        tables = extract_tables(
            segment_lines,
            0,
            len(segment_lines),
            allow_optional_tags=True,
        )
        marker_lines: list[str] = []
        for raw_line in segment_lines:
            stripped_line = raw_line.strip()
            if stripped_line.startswith(("<!-- BEGIN AUTO-GENERATED", "<!-- END AUTO-GENERATED")):
                marker_lines.append(stripped_line)
        yaml_schemas: list[YamlSchema] = []
        for _, block_lines in iter_yaml_blocks(segment_lines):
            if yaml is None:
                raise RuntimeError("PyYAML is required to validate template YAML blocks")
            try:
                loaded = yaml.safe_load("\n".join(block_lines))
            except Exception as exc:
                raise RuntimeError(f"{template_path}: failed to parse YAML block: {exc}") from exc
            if loaded is None:
                loaded = {}
            yaml_schemas.append(build_yaml_schema(loaded))
        specs.append(
            SectionSpec(
                numbering=numbering,
                level=level,
                title=title,
                preamble_order=order,
                preamble_requires_marker=marker_map,
                tables=tuple(tables),
                yaml_schemas=tuple(yaml_schemas),
                required_markers=tuple(marker_lines),
            ),
        )
        if order:
            last_label = order[-1]
            if marker_map.get(last_label, False):
                raise RuntimeError(
                    f"{template_path}: last preamble entry '{last_label}' must not end with '{PREAMBLE_DIVIDER}'",
                )
    return specs


def ensure_template_requirements(template_path: Path) -> None:
    lines = template_path.read_text(encoding="utf-8").splitlines()
    front_matter = parse_front_matter(lines)
    if not front_matter:
        raise RuntimeError(f"{template_path}: template missing usable front matter")
    index = build_front_matter_index(front_matter)
    missing_keys = sorted(key for key in REQUIRED_FRONT_MATTER_KEYS if key not in index)
    if missing_keys:
        joined = ", ".join(missing_keys)
        raise RuntimeError(f"{template_path}: front matter missing required keys: {joined}")

    try:
        header_idx = find_section_header(lines, DOCUMENT_CONTROLS_HEADER)
    except ValueError as exc:  # pragma: no cover - template must always comply
        raise RuntimeError(f"{template_path}: {exc}") from exc

    rows = extract_table_rows(lines, header_idx)
    if len(rows) < 2:
        raise RuntimeError(f"{template_path}: document controls table incomplete")
    header_row, _, table_data = parse_table(rows)
    if "Field" not in header_row or "Value" not in header_row:
        raise RuntimeError(f"{template_path}: document controls header must contain 'Field' and 'Value'")

    label_keys: set[str] = set()
    for label, _ in table_data:
        normalized = normalize_key(label)
        label_keys.add(normalized)
        label_keys.update(key_variants(normalized))
    required_controls = TEMPLATE_REQUIREMENTS.required_document_control_keys
    missing_controls = [key for key in required_controls if normalize_key(key) not in label_keys]
    if missing_controls:
        formatted = ", ".join(format_label(key) for key in missing_controls)
        raise RuntimeError(
            f"{template_path}: document controls table missing required rows for: {formatted}",
        )


def walk_targets(paths: Iterable[Path]) -> Iterator[Path]:
    seen: set[Path] = set()
    for path in paths:
        if not path.exists():
            print(f"warning: {path} does not exist; skipping", file=sys.stderr)
            continue
        if path.is_dir():
            for candidate in sorted(path.rglob("*.md")):
                if candidate.name == TEMPLATE_NAME:
                    continue
                resolved = candidate.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield resolved
        else:
            resolved = path.resolve()
            if resolved.name != TEMPLATE_NAME and resolved not in seen:
                seen.add(resolved)
                yield resolved


def check_document_controls(path: Path, lines: Sequence[str]) -> list[str]:
    errors: list[str] = []
    front_matter = parse_front_matter(lines)
    if not front_matter:
        errors.append(f"{path}: missing or invalid YAML front matter")
        return errors

    front_index = build_front_matter_index(front_matter)
    missing_required = [key for key in REQUIRED_FRONT_MATTER_KEYS if key not in front_index]
    if missing_required:
        errors.append(
            f"{path}: front matter missing required keys: "
            f"{', '.join(format_label(key) for key in missing_required)}",
        )

    try:
        header_idx = find_section_header(lines, DOCUMENT_CONTROLS_HEADER)
    except ValueError:
        errors.append(f"{path}: missing '{DOCUMENT_CONTROLS_HEADER}' section")
        return errors

    rows = extract_table_rows(lines, header_idx)
    if len(rows) < 2:
        errors.append(f"{path}: document controls table incomplete")
        return errors

    try:
        header_row, _, table_data = parse_table(rows)
    except ValueError as exc:
        errors.append(f"{path}: {exc}")
        return errors

    if "Field" not in header_row or "Value" not in header_row:
        errors.append(f"{path}: document controls table missing 'Field'/'Value' header")

    table_map: dict[str, tuple[str, str]] = {}
    duplicates: list[str] = []
    for label, value in table_data:
        normalized = normalize_key(label)
        if normalized in table_map:
            duplicates.append(label)
            continue
        table_map[normalized] = (label, value)
    if duplicates:
        joined = ", ".join(duplicates)
        errors.append(f"{path}: document controls contains duplicate fields: {joined}")

    excluded = {normalize_key(item) for item in EXCLUDED_CONTROL_KEYS}
    matched_labels: set[str] = set()
    for key, value in front_matter.items():
        normalized_key = normalize_key(key)
        if normalized_key in excluded:
            continue

        expected = stringify(value).strip()
        if not expected and normalized_key not in OPTIONAL_KEYS:
            errors.append(f"{path}: front matter key '{key}' must not be empty")

        variants = key_variants(key)
        match: tuple[str, str] | None = None
        match_norm: str | None = None
        for variant in variants:
            if variant in table_map:
                match_norm = variant
                match = table_map[variant]
                break

        if match is None:
            errors.append(f"{path}: document controls missing field '{format_label(key)}'")
            continue

        matched_labels.add(match_norm or normalize_key(match[0]))
        label, present_value = match
        actual_value = present_value.strip()

        if expected and not actual_value:
            errors.append(f"{path}: document controls field '{label}' must not be empty")
        elif not expected and actual_value:
            errors.append(
                f"{path}: document controls field '{label}' contains '{actual_value}' but front matter is blank",
            )
        elif expected and actual_value and expected != actual_value:
            errors.append(
                f"{path}: document controls field '{label}' value '{actual_value}' does not match front matter '{expected}'",
            )

    optional_labels = OPTIONAL_KEYS
    for normalized, (label, _) in table_map.items():
        if normalized in matched_labels:
            continue
        if normalized in optional_labels:
            continue
        errors.append(f"{path}: document controls has unexpected field '{label}'")

    if DOCUMENT_CONTROLS_BEGIN not in lines or DOCUMENT_CONTROLS_END not in lines:
        errors.append(
            f"{path}: document controls table must be wrapped with '{DOCUMENT_CONTROLS_BEGIN}' and '{DOCUMENT_CONTROLS_END}' markers",
        )

    return errors


def validate_sections(path: Path, template_specs: list[SectionSpec], lines: Sequence[str]) -> list[str]:
    errors: list[str] = []
    content = "\n".join(lines)
    doc_sections = parse_sections(content)
    section_lookup = {num: (idx, title, level) for num, level, title, idx in doc_sections}
    section_order = {num: position for position, (num, _, _, _) in enumerate(doc_sections)}
    section_bounds: dict[tuple[int, ...], tuple[int, int]] = {}
    for idx, (numbering, level, _, line_no) in enumerate(doc_sections):
        start_idx = line_no - 1
        next_idx = len(lines)
        for _, candidate_level, _, candidate_line in doc_sections[idx + 1 :]: # candidate_numbering replaced with _ (not used)
            if candidate_level <= level:
                next_idx = candidate_line - 1
                break
        section_bounds[numbering] = (start_idx, next_idx)

    previous_position = -1
    for spec in template_specs:
        numbering = spec.numbering
        human = ".".join(str(n) for n in numbering)

        if numbering not in section_lookup:
            errors.append(f"{path}: missing section {human}")
            continue

        position = section_order[numbering]
        if position <= previous_position:
            errors.append(f"{path}: section {human} appears out of order")
        previous_position = position

        line_no, actual_title, actual_level = section_lookup[numbering]

        # Ensure heading level matches template (e.g., ## vs ###)
        if actual_level != spec.level:
            errors.append(
                f"{path}: section {human} uses heading level {actual_level} but template requires {spec.level}",
            )

        # Ensure heading title matches template exactly, allowing optional binding suffix
        def _strip_suffix(value: str) -> tuple[str, str | None]:
            stripped = value.strip()
            if stripped.endswith("}") and "{#" in stripped:
                attr_index = stripped.rfind("{#")
                stripped = stripped[:attr_index].rstrip()
            for suffix in (" (binding)", " (informative)", " (normative)"):
                if stripped.endswith(suffix):
                    return stripped[: -len(suffix)].rstrip(), suffix.strip()
            return stripped, None

        actual_title_base, _ = _strip_suffix(actual_title)
        spec_title_base, _ = _strip_suffix(spec.title.strip())

        # Enforce title case (excluding suffix) for headings
        def _is_title_case(text: str) -> bool:
            words = [word for word in text.split() if word]
            for index, word in enumerate(words):
                if word[0].isdigit():
                    continue
                cleaned = word.strip("&()[]{}-/_")
                if not cleaned:
                    continue
                if cleaned.isupper():
                    continue
                if index > 0 and cleaned.lower() in LOWERCASE_WORDS:
                    continue
                if not cleaned[0].isupper():
                    return False
            return True

        if not _is_title_case(actual_title_base):
            errors.append(
                f"{path}: section {human} heading '{actual_title.strip()}' must use Title Case before suffix",
            )

        if actual_title_base != spec_title_base:
            errors.append(
                f"{path}: section {human} heading '{actual_title.strip()}' does not match template '{spec.title.strip()}'",
            )

        preamble_lines = gather_preamble(lines, line_no)
        start_idx, next_idx = section_bounds.get(numbering, (line_no - 1, len(lines)))
        section_slice = lines[start_idx : (next_idx if next_idx > start_idx else len(lines))]

        if spec.required_markers:
            present = {segment.strip() for segment in section_slice}
            for marker in spec.required_markers:
                if marker not in present:
                    errors.append(f"{path}: section {human} missing marker '{marker}' from template")

        if spec.preamble_order:
            if not preamble_lines:
                errors.append(f"{path}: section {human} missing preamble block")
                continue
            if len(preamble_lines) < len(spec.preamble_order):
                missing = spec.preamble_order[len(preamble_lines):]
                errors.append(f"{path}: section {human} missing preamble entries: {', '.join(missing)}")
                continue
            for expected, (_, actual_label, body) in zip(spec.preamble_order, preamble_lines, strict=False):
                if actual_label != expected:
                    errors.append(f"{path}: section {human} expected preamble entry '{expected}' but found '{actual_label}'")
                text = body.rstrip()
                has_marker = text.endswith(PREAMBLE_DIVIDER)
                if has_marker:
                    text = text[: -len(PREAMBLE_DIVIDER)].rstrip()
                if text.endswith(" *"):
                    errors.append(
                        f"{path}: section {human} preamble entry '{actual_label}' must not end with ' *'",
                    )
                requires_marker = spec.preamble_requires_marker.get(actual_label, False)
                if requires_marker and not has_marker:
                    errors.append(
                        f"{path}: section {human} preamble entry '{actual_label}' must end with '{PREAMBLE_DIVIDER}'",
                    )
                if not requires_marker and has_marker:
                    errors.append(
                        f"{path}: section {human} preamble entry '{actual_label}' must not end with '{PREAMBLE_DIVIDER}'",
                    )
            if len(preamble_lines) > len(spec.preamble_order):
                extras = [label for _, label, _ in preamble_lines[len(spec.preamble_order):]]
                errors.append(f"{path}: section {human} has unexpected preamble entries: {', '.join(extras)}")
        elif preamble_lines:
            labels = [label for _, label, _ in preamble_lines]
            errors.append(f"{path}: section {human} should not have preamble entries but found: {', '.join(labels)}")

        if spec.tables:
            doc_tables = extract_tables(
                section_slice,
                0,
                len(section_slice),
                allow_optional_tags=False,
            )
            used = [False] * len(doc_tables)
            for template_table in spec.tables:
                header_display = " | ".join(template_table.header)
                match_idx: int | None = None
                for idx_table, candidate in enumerate(doc_tables):
                    if used[idx_table]:
                        continue
                    if tuple(candidate.header) == template_table.header:
                        match_idx = idx_table
                        break
                if match_idx is None:
                    errors.append(
                        f"{path}: section {human} missing table with header '{header_display}'",
                    )
                    continue
                used[match_idx] = True
                candidate_table = doc_tables[match_idx]
                if not candidate_table.rows:
                    errors.append(
                        f"{path}: section {human} table '{header_display}' must contain at least one data row",
                    )
                candidate_first_cells = {
                    row.first_cell for row in candidate_table.rows if row.first_cell
                }
                for row_spec in template_table.rows:
                    if not row_spec.first_cell or row_spec.optional:
                        continue
                    if row_spec.first_cell not in candidate_first_cells:
                        errors.append(
                            f"{path}: section {human} table '{header_display}' missing row '{row_spec.first_cell}'",
                        )

        if spec.yaml_schemas:
            start_idx, next_idx = section_bounds.get(numbering, (line_no - 1, len(lines)))
            content_start = start_idx + 1
            content_end = next_idx if next_idx > content_start else len(lines)
            segment_lines = lines[max(content_start, 0) : min(content_end, len(lines))]
            yaml_blocks = [block for _, block in iter_yaml_blocks(segment_lines)]
            if not yaml_blocks:
                errors.append(f"{path}: section {human} missing required YAML block(s) from template")
            else:
                used_indices: set[int] = set()
                for schema in spec.yaml_schemas:
                    matched = False
                    for idx_block, block_lines in enumerate(yaml_blocks):
                        if idx_block in used_indices:
                            continue
                        if yaml is None:
                            errors.append(f"{path}: section {human} cannot validate YAML without PyYAML installed")
                            matched = True
                            break
                        try:
                            loaded = yaml.safe_load("\n".join(block_lines))
                        except Exception as exc:
                            errors.append(f"{path}: section {human} contains invalid YAML: {exc}")
                            used_indices.add(idx_block)
                            matched = True
                            break
                        candidate: Any = loaded if loaded is not None else {}
                        if schema.kind == "mapping" and isinstance(candidate, dict):
                            field_keys: set[str] = set(schema.fields.keys()) if schema.fields else set()
                            loaded_mapping = cast("dict[str, Any]", candidate)
                            if field_keys and field_keys.isdisjoint(loaded_mapping.keys()):
                                continue
                        validation_errors: list[str] = []
                        validate_yaml_schema(schema, candidate, [], validation_errors)
                        if validation_errors:
                            for issue in validation_errors:
                                errors.append(f"{path}: section {human} YAML {issue}")
                            used_indices.add(idx_block)
                            matched = True
                            break
                        used_indices.add(idx_block)
                        matched = True
                        break
                    if not matched:
                        errors.append(f"{path}: section {human} missing required YAML block(s) from template")

    return errors


def main() -> int:
    args = parse_args()
    targets = list(walk_targets(args.paths))
    if not targets:
        print("No markdown targets found.", file=sys.stderr)
        return 1

    issues: list[str] = []
    template_cache: dict[Path, tuple[bool, list[SectionSpec]]] = {}
    for target in targets:
        lines = target.read_text(encoding="utf-8").splitlines()
        issues.extend(check_document_controls(target, lines))
        disabled_template = False
        template_specs: list[SectionSpec] = []
        if not args.frontmatter:
            template_path = find_template(target, args.template)
            if template_path in template_cache:
                disabled_template, template_specs = template_cache[template_path]
            elif template_disabled(template_path):
                disabled_template = True
                if template_path not in DISABLED_TEMPLATE_MESSAGES:
                    print(
                        f"warning: template {template_path} marked as disabled; skipping section validation.",
                        file=sys.stderr,
                    )
                    DISABLED_TEMPLATE_MESSAGES.add(template_path)
                template_cache[template_path] = (True, [])
            else:
                ensure_template_requirements(template_path)
                template_specs = build_template_spec(template_path)
                template_cache[template_path] = (False, template_specs)
        if not args.frontmatter and not disabled_template:
            issues.extend(validate_sections(target, template_specs, lines))

    if issues:
        for issue in issues:
            print(issue)
        return 1

    if args.frontmatter:
        print("All documents have synced front matter and document controls.")
    else:
        print("All service specifications comply with the template.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
