#!/usr/bin/env python3
"""Validate documentation templates for required metadata and controls."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from collections.abc import Iterable, Iterator, Mapping, Sequence

from doc_tools.config import paths
from doc_tools.check.requirements import OPTIONAL_KEYS, TEMPLATE_REQUIREMENTS
from doc_tools.check.utils import extract_table_rows, find_section_header, parse_table
from doc_tools.config.header_includes import HEADER_INCLUDES_CONFIG
from doc_tools.common.doc_utils import format_label, normalize_key, parse_front_matter, stringify

DEFAULT_TARGETS: tuple[Path, ...] = (paths.DOCS_ROOT,)
DOCUMENT_CONTROLS_HEADER = "## Document Controls"
TEMPLATE_NAME = "_template.md"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate documentation templates (front matter, header-includes, document controls).",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Template files or directories to scan (defaults to docs/ root).",
    )
    return parser.parse_args(argv)


def _resolve_targets(raw_paths: Sequence[Path]) -> list[Path]:
    if not raw_paths:
        return [paths.DOCS_ROOT]
    return list(raw_paths)


def iter_templates(candidates: Iterable[Path]) -> Iterator[Path]:
    seen: set[Path] = set()
    for candidate in candidates:
        if not candidate.exists():
            print(f"[templates-check] warning: {candidate} does not exist; skipping", file=sys.stderr)
            continue
        if candidate.is_dir():
            for path in sorted(candidate.rglob(TEMPLATE_NAME)):
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield resolved
        else:
            resolved = candidate.resolve()
            if resolved.name == TEMPLATE_NAME and resolved not in seen:
                seen.add(resolved)
                yield resolved


def _string_value(value: object) -> str:
    return stringify(value).strip()


def validate_front_matter(path: Path, front_matter: Mapping[str, object]) -> list[str]:
    errors: list[str] = []
    required_keys = TEMPLATE_REQUIREMENTS.required_front_matter_keys
    missing = [key for key in required_keys if key not in front_matter]
    if missing:
        formatted = ", ".join(format_label(key) for key in missing)
        errors.append(f"{path}: front matter missing required keys: {formatted}")
    for key in required_keys:
        if key not in front_matter:
            continue
        value = _string_value(front_matter[key])
        if not value and key not in OPTIONAL_KEYS:
            errors.append(f"{path}: front matter key '{key}' must not be empty")
    return errors


def validate_document_controls(path: Path, lines: Sequence[str]) -> list[str]:
    errors: list[str] = []
    try:
        header_idx = find_section_header(lines, DOCUMENT_CONTROLS_HEADER)
    except ValueError:
        return [f"{path}: missing '{DOCUMENT_CONTROLS_HEADER}' section"]
    rows = extract_table_rows(lines, header_idx)
    if len(rows) < 2:
        return [f"{path}: document controls table incomplete"]
    try:
        header_row, _, table_data = parse_table(rows)
    except ValueError as exc:
        return [f"{path}: {exc}"]
    if "| Field" not in header_row or "| Value" not in header_row:
        errors.append(f"{path}: document controls header must contain 'Field' and 'Value'")
        return errors

    table_map: dict[str, tuple[str, str]] = {}
    duplicates: list[str] = []
    for label, value in table_data:
        normalized = normalize_key(label)
        if normalized in table_map:
            duplicates.append(label)
            continue
        table_map[normalized] = (label, value.strip())
    if duplicates:
        errors.append(f"{path}: document controls contains duplicate fields: {', '.join(duplicates)}")

    required_controls = TEMPLATE_REQUIREMENTS.required_document_control_keys
    required_norm = {normalize_key(key) for key in required_controls}
    missing_rows = [
        format_label(key) for key in required_controls if normalize_key(key) not in table_map
    ]
    if missing_rows:
        errors.append(
            f"{path}: document controls missing required rows: {', '.join(missing_rows)}",
        )

    optional_norm = {normalize_key(key) for key in OPTIONAL_KEYS}
    for normalized_key, (label, value) in table_map.items():
        if normalized_key not in required_norm:
            continue
        if not value and normalized_key not in optional_norm:
            errors.append(f"{path}: document controls field '{label}' must not be empty")
    return errors


def check_template(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    front = parse_front_matter(lines)
    if not front:
        return [f"{path}: missing usable front matter"]
    errors = validate_front_matter(path, front)
    errors.extend(validate_document_controls(path, lines))
    return errors


def _legacy_placeholder_warnings() -> list[str]:
    tokens = HEADER_INCLUDES_CONFIG.legacy_front_matter_tokens
    if not tokens:
        return []
    formatted = ", ".join(f"{{{{{token}}}}} -> {{<{token}>}}" for token in sorted(tokens))
    return [f"warning: header-includes config uses legacy placeholders; migrate {formatted}"]


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    targets = _resolve_targets(args.paths)
    templates = list(iter_templates(targets))
    if not templates:
        print("No template files found.", file=sys.stderr)
        return 1

    errors: list[str] = []
    for template in templates:
        errors.extend(check_template(template))

    warnings = _legacy_placeholder_warnings()

    for issue in errors:
        print(issue)
    for warning in warnings:
        print(warning)

    return 1 if errors else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
