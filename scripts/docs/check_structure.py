#!/usr/bin/env python3
"""Validate documentation structure against the canonical template.

By default the checker inspects source documents under
``docs/src`` and ensures:

* Numeric sections (``## 1``, ``### 3.1`` …) appear in the same order as 
  their accompanying ``_template.md`` file.
* Each section contains the preamble entries declared in the template, in the
  same order, with every entry ending in ``**|**`` (and never duplicated).
* No unexpected preamble entries are present.
* The "Document controls" table contains all required rows, values are present,
  **and** the values match the YAML front matter.

Typical usage (CLI/CI friendly):

    python scripts/docs/check_structure.py
    python scripts/docs/check_structure.py docs/src/apps/web-app.md
    python scripts/docs/check_structure.py docs/src/services docs/src/overview
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from scripts.docs import doc_utils  # type: ignore  # noqa: E402

TEMPLATE_NAME = "_template.md"
HEADING_RE = re.compile(r"^(#{2,6})\s+(.*)")
PREAMBLE_RE = re.compile(r"^\*\*(.+?):\*\*\s*(.*)$")
DOCUMENT_CONTROLS_HEADER = "## Document Controls"
EXCLUDED_FRONT_MATTER_KEYS = {
    "title",
    "subtitle",
    "header-includes",
}
OPTIONAL_CONTROL_KEYS = {"approved_by", "approved_date"}

REQUIRED_FRONT_MATTER_KEYS = {
    "title",
    "subtitle",
    "authors",
    "version",
    "status",
    "classification",
    "last_updated",
    "updated_by",
    "owners",
    "reviewers",
    "approvers",
    "approved_by",
    "approved_date",
}

LOWERCASE_WORDS = {"and", "or", "the", "a", "an", "of", "in", "on", "for", "to", "with", "by"}
DISABLED_TEMPLATE_MESSAGES: set[Path] = set()


@dataclass(frozen=True)
class SectionSpec:
    numbering: Tuple[int, ...]
    level: int
    title: str
    preamble_order: Tuple[str, ...]
    preamble_requires_marker: Dict[str, bool]


def normalize_key(value: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", value.lower())
    return "_".join(token for token in tokens if token)


def key_variants(raw_key: str) -> Tuple[str, ...]:
    base = normalize_key(raw_key)
    variants: List[str] = []
    if base:
        variants.append(base)
        if base.endswith("s") and not base.endswith("ss"):
            trimmed = base[:-1]
            if trimmed:
                variants.append(trimmed)
        elif not base.endswith("s"):
            variants.append(f"{base}s")
    return tuple(dict.fromkeys(variants))


def format_label(key: str) -> str:
    parts = re.split(r"[_\s-]+", key.strip())
    words: List[str] = []
    for index, part in enumerate(parts):
        if not part:
            continue
        lower = part.lower()
        if index > 0 and lower in LOWERCASE_WORDS:
            words.append(lower)
        else:
            words.append(part.capitalize())
    return " ".join(words) if words else key


def build_front_matter_index(front_matter: Dict[str, Any]) -> Dict[str, List[str]]:
    index: Dict[str, List[str]] = {}
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


def find_section_header(lines: Sequence[str], header: str) -> int:
    for idx, line in enumerate(lines):
        if line.strip().lower() == header.lower():
            return idx
    raise ValueError(f"missing '{header}' section")


def extract_table_rows(lines: Sequence[str], start_idx: int) -> List[str]:
    rows: List[str] = []
    idx = start_idx + 1
    while idx < len(lines):
        stripped = lines[idx].lstrip()
        if stripped.startswith("|"):
            break
        idx += 1
    while idx < len(lines):
        stripped = lines[idx].lstrip()
        if not stripped.startswith("|"):
            break
        rows.append(stripped)
        idx += 1
    return rows


def parse_table(rows: Sequence[str]) -> Tuple[str, str, List[Tuple[str, str]]]:
    if len(rows) < 2:
        raise ValueError("document controls table incomplete")
    header_row = rows[0]
    separator_row = rows[1]
    data: List[Tuple[str, str]] = []
    for raw in rows[2:]:
        cells = [cell.strip() for cell in raw.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        field, value = cells[0], cells[1]
        data.append((field, value))
    return header_row, separator_row, data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate docs against the canonical template")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path("docs/src")],
        help="Markdown files or directories to validate (defaults to docs/src)",
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


def extract_numbering(title: str) -> Tuple[int, ...] | None:
    title = title.strip()
    if m := re.match(r"^(\d+)\)", title):
        return (int(m.group(1)),)
    if m := re.match(r"^(\d+(?:\.\d+)+)", title):
        return tuple(int(part) for part in m.group(1).split("."))
    return None


def parse_sections(markdown: str) -> List[Tuple[Tuple[int, ...], int, str, int]]:
    sections: List[Tuple[Tuple[int, ...], int, str, int]] = []
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


def gather_preamble(lines: Sequence[str], start_idx: int) -> List[Tuple[int, str, str]]:
    entries: List[Tuple[int, str, str]] = []
    idx = start_idx
    while idx < len(lines):
        line = lines[idx]
        trimmed = line.strip()
        if not trimmed:
            idx += 1
            continue
        m = PREAMBLE_RE.match(trimmed)
        if not m:
            break
        label_raw, body = m.groups()
        label = label_raw.strip()
        entries.append((idx, label, body.strip()))
        idx += 1
    return entries


def build_template_spec(template_path: Path) -> List[SectionSpec]:
    content = template_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    specs: List[SectionSpec] = []
    for numbering, level, title, line_no in parse_sections(content):
        preamble_entries = gather_preamble(lines, line_no)
        order = tuple(label for _, label, _ in preamble_entries)
        marker_map: Dict[str, bool] = {}
        for _, label, body in preamble_entries:
            marker_map[label] = body.endswith("**|**")
        specs.append(SectionSpec(numbering, level, title, order, marker_map))
    return specs


def ensure_template_requirements(template_path: Path) -> None:
    lines = template_path.read_text(encoding="utf-8").splitlines()
    front_matter = doc_utils.parse_front_matter(lines)
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
    excluded = {normalize_key(key) for key in EXCLUDED_FRONT_MATTER_KEYS}
    required_controls = [key for key in REQUIRED_FRONT_MATTER_KEYS if key not in excluded]
    missing_controls = [key for key in required_controls if key not in label_keys]
    if missing_controls:
        formatted = ", ".join(format_label(key) for key in missing_controls)
        raise RuntimeError(
            f"{template_path}: document controls table missing required rows for: {formatted}"
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
def check_document_controls(path: Path, lines: Sequence[str]) -> List[str]:
    errors: List[str] = []
    front_matter = doc_utils.parse_front_matter(lines)
    if not front_matter:
        errors.append(f"{path}: missing or invalid YAML front matter")
        return errors

    front_index = build_front_matter_index(front_matter)
    missing_required = [key for key in REQUIRED_FRONT_MATTER_KEYS if key not in front_index]
    if missing_required:
        errors.append(
            f"{path}: front matter missing required keys: "
            f"{', '.join(format_label(key) for key in missing_required)}"
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

    table_map: Dict[str, Tuple[str, str]] = {}
    duplicates: List[str] = []
    for label, value in table_data:
        normalized = normalize_key(label)
        if normalized in table_map:
            duplicates.append(label)
            continue
        table_map[normalized] = (label, value)
    if duplicates:
        joined = ", ".join(duplicates)
        errors.append(f"{path}: document controls contains duplicate fields: {joined}")

    excluded = {normalize_key(item) for item in EXCLUDED_FRONT_MATTER_KEYS}
    matched_labels: set[str] = set()
    for key, value in front_matter.items():
        normalized_key = normalize_key(key)
        if normalized_key in excluded:
            continue

        expected = doc_utils.stringify(value).strip()
        if not expected and normalized_key not in OPTIONAL_CONTROL_KEYS:
            errors.append(f"{path}: front matter key '{key}' must not be empty")

        variants = key_variants(key)
        match: Optional[Tuple[str, str]] = None
        match_norm: Optional[str] = None
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
                f"{path}: document controls field '{label}' contains '{actual_value}' but front matter is blank"
            )
        elif expected and actual_value and expected != actual_value:
            errors.append(
                f"{path}: document controls field '{label}' value '{actual_value}' does not match front matter '{expected}'"
            )

    optional_labels = OPTIONAL_CONTROL_KEYS
    for normalized, (label, _) in table_map.items():
        if normalized in matched_labels:
            continue
        if normalized in optional_labels:
            continue
        errors.append(f"{path}: document controls has unexpected field '{label}'")

    return errors


def validate_sections(path: Path, template_specs: List[SectionSpec], lines: Sequence[str]) -> List[str]:
    errors: List[str] = []
    content = "\n".join(lines)
    doc_sections = parse_sections(content)
    section_lookup = {num: (idx, title, level) for num, level, title, idx in doc_sections}
    section_order = {num: position for position, (num, _, _, _) in enumerate(doc_sections)}

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
                f"{path}: section {human} uses heading level {actual_level} but template requires {spec.level}"
            )

        # Ensure heading title matches template exactly, allowing optional binding suffix
        def _strip_suffix(value: str) -> Tuple[str, Optional[str]]:
            stripped = value.strip()
            if stripped.endswith('}') and '{#' in stripped:
                attr_index = stripped.rfind('{#')
                stripped = stripped[:attr_index].rstrip()
            for suffix in (" (binding)", " (informative)", " (normative)"):
                if stripped.endswith(suffix):
                    return stripped[: -len(suffix)].rstrip(), suffix.strip()
            return stripped, None

        actual_title_base, _ = _strip_suffix(actual_title)
        spec_title_base = spec.title.strip()

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
                f"{path}: section {human} heading '{actual_title.strip()}' must use Title Case before suffix"
            )

        if actual_title_base != spec_title_base:
            errors.append(
                f"{path}: section {human} heading '{actual_title.strip()}' does not match template '{spec.title.strip()}'"
            )

        preamble_lines = gather_preamble(lines, line_no)

        if spec.preamble_order:
            if not preamble_lines:
                errors.append(f"{path}: section {human} missing preamble block")
                continue
            if len(preamble_lines) < len(spec.preamble_order):
                missing = spec.preamble_order[len(preamble_lines):]
                errors.append(f"{path}: section {human} missing preamble entries: {', '.join(missing)}")
                continue
            for expected, (_, actual_label, body) in zip(spec.preamble_order, preamble_lines):
                if actual_label != expected:
                    errors.append(f"{path}: section {human} expected preamble entry '{expected}' but found '{actual_label}'")
                text = body.strip()
                requires_marker = spec.preamble_requires_marker.get(actual_label, True)
                has_marker = text.endswith("**|**")
                if requires_marker and not has_marker:
                    errors.append(f"{path}: section {human} preamble entry '{actual_label}' must end with '**|**'")
                if not requires_marker and has_marker:
                    errors.append(f"{path}: section {human} preamble entry '{actual_label}' must not end with '**|**'")
                if text.endswith("**|****|**") or text.endswith("**|** **|**"):
                    errors.append(f"{path}: section {human} preamble entry '{actual_label}' contains duplicate '**|**' markers")
            if len(preamble_lines) > len(spec.preamble_order):
                extras = [label for _, label, _ in preamble_lines[len(spec.preamble_order):]]
                errors.append(f"{path}: section {human} has unexpected preamble entries: {', '.join(extras)}")
        else:
            if preamble_lines:
                labels = [label for _, label, _ in preamble_lines]
                errors.append(f"{path}: section {human} should not have preamble entries but found: {', '.join(labels)}")

    return errors


def main() -> int:
    args = parse_args()
    targets = list(walk_targets(args.paths))
    if not targets:
        print("No markdown targets found.", file=sys.stderr)
        return 1

    issues: List[str] = []
    template_cache: Dict[Path, Tuple[bool, List[SectionSpec]]] = {}
    for target in targets:
        lines = target.read_text(encoding="utf-8").splitlines()
        issues.extend(check_document_controls(target, lines))
        disabled_template = False
        template_specs: List[SectionSpec] = []
        if not args.frontmatter:
            template_path = find_template(target, args.template)
            if template_path in template_cache:
                disabled_template, template_specs = template_cache[template_path]
            else:
                if template_disabled(template_path):
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
    sys.exit(main())
