#!/usr/bin/env python3
"""Validate documentation structure against the canonical template.

By default the checker inspects service specifications under
``docs/src/services`` and ensures:

* Numeric sections (``## 1``, ``### 3.1`` …) appear in the same order as
  ``docs/src/services/_template.md``.
* Each section contains the preamble entries declared in the template, in the
  same order, with every entry ending in ``**|**`` (and never duplicated).
* No unexpected preamble entries are present.
* The "Document controls" table contains all required rows, values are present,
  **and** the values match the YAML front matter.

Typical usage (CLI/CI friendly):

    python scripts/docs/check_structure.py
    python scripts/docs/check_structure.py docs/src/services/web-app.md
    python scripts/docs/check_structure.py docs/src/services docs/src/overview
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

TEMPLATE_NAME = "_template.md"
HEADING_RE = re.compile(r"^(#{2,6})\s+(.*)")
PREAMBLE_RE = re.compile(r"^\*\*(.+?):\*\*\s*(.*)$")
DOCUMENT_CONTROLS_HEADER = "## Document Controls"
DOCUMENT_CONTROLS_FIELDS = (
    "Authors",
    "Version",
    "Status",
    "Classification",
    "Last updated",
    "Owners",
    "Reviewers",
    "Approvers",
    "Approved by",
    "Approved date",
)
OPTIONAL_CONTROL_FIELDS = {"Approved by", "Approved date"}

LABEL_NORMALISATION = {
    "failure modes & handling": "Failures & handling",
    "failure mode & handling": "Failures & handling",
    "failures & handling": "Failures & handling",
    "handling": "Failures & handling",
    "purpose": "Purpose",
    "contract": "Contract",
    "state": "State",
    "observability": "Observability",
    "breadcrumbs": "Breadcrumbs",
    "references": "References",
}


@dataclass(frozen=True)
class SectionSpec:
    numbering: Tuple[int, ...]
    level: int
    title: str
    preamble_order: Tuple[str, ...]
    preamble_requires_marker: Dict[str, bool]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate docs against the canonical template")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path("docs/src/services")],
        help="Markdown files or directories to validate (defaults to docs/src/services)",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=None,
        help="Override `_template.md` path (defaults to nearest ancestor of first target)",
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
    fallback = Path("docs/src/services") / TEMPLATE_NAME
    if fallback.is_file():
        return fallback.resolve()
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
        label = LABEL_NORMALISATION.get(label_raw.lower(), label_raw)
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


def parse_front_matter(lines: Sequence[str]) -> Dict[str, Any]:
    if not lines or lines[0].strip() != "---":
        return {}
    fm_lines: List[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)
    if not fm_lines:
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    try:
        return yaml.safe_load("\n".join(fm_lines)) or {}
    except Exception:
        return {}


def check_document_controls(path: Path, lines: Sequence[str]) -> List[str]:
    errors: List[str] = []
    front_matter = parse_front_matter(lines)
    try:
        header_idx = next(i for i, line in enumerate(lines) if line.strip().lower() == DOCUMENT_CONTROLS_HEADER.lower())
    except StopIteration:
        errors.append(f"{path}: missing '{DOCUMENT_CONTROLS_HEADER}' section")
        return errors

    rows: List[str] = []
    idx = header_idx + 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    while idx < len(lines) and lines[idx].startswith("|"):
        rows.append(lines[idx])
        idx += 1

    if len(rows) < 3:
        errors.append(f"{path}: document controls table incomplete")
        return errors

    header = rows[0]
    if "Field" not in header or "Value" not in header:
        errors.append(f"{path}: document controls table missing 'Field'/'Value' header")

    fields_present: Dict[str, str] = {}
    for row in rows[2:]:  # skip header and separator
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        field, value = cells[0], cells[1]
        fields_present[field] = value

    def _as_str_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, (str, bytes)):
            return [str(value).strip()]
        if isinstance(value, Iterable):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()]

    expected_values: Dict[str, str] = {}
    if front_matter:
        authors = _as_str_list(front_matter.get("author"))
        expected_values = {
            "Authors": "; ".join(authors),
            "Version": str(front_matter.get("version", "")).strip(),
            "Status": str(front_matter.get("status", "")).strip(),
            "Classification": str(front_matter.get("classification", "")).strip(),
            "Last updated": str(front_matter.get("last_updated", "")).strip(),
            "Owners": "; ".join(_as_str_list(front_matter.get("owners"))),
            "Reviewers": "; ".join(_as_str_list(front_matter.get("reviewers"))),
            "Approvers": "; ".join(_as_str_list(front_matter.get("approvers"))),
        }

    for field in DOCUMENT_CONTROLS_FIELDS:
        if field not in fields_present:
            errors.append(f"{path}: document controls missing field '{field}'")
            continue
        value = fields_present[field]
        if not value and field not in OPTIONAL_CONTROL_FIELDS:
            errors.append(f"{path}: document controls field '{field}' must not be empty")
        expected = expected_values.get(field)
        if expected is not None:
            if expected:
                if value.strip() != expected.strip():
                    errors.append(
                        f"{path}: document controls field '{field}' value '{value.strip()}' does not match front matter '{expected.strip()}'"
                    )
            else:
                if value.strip() and field not in OPTIONAL_CONTROL_FIELDS:
                    errors.append(
                        f"{path}: document controls field '{field}' contains '{value.strip()}' but front matter is blank"
                    )
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
            for suffix in (" (binding)", " (informative)", " (normative)"):
                if stripped.endswith(suffix):
                    return stripped[: -len(suffix)].rstrip(), suffix.strip()
            return stripped, None

        actual_title_base, _ = _strip_suffix(actual_title)
        spec_title_base = spec.title.strip()

        # Enforce title case (excluding suffix) for headings
        def _is_title_case(text: str) -> bool:
            lowercase_allowed = {"and", "or", "the", "a", "an", "of", "in", "on", "for", "to", "with", "by"}

            words = [word for word in text.split() if word]
            for index, word in enumerate(words):
                if word[0].isdigit():
                    continue
                cleaned = word.strip("&()[]{}-/_")
                if not cleaned:
                    continue
                if cleaned.isupper():
                    continue
                if index > 0 and cleaned.lower() in lowercase_allowed:
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

    template_path = find_template(targets[0], args.template)
    template_specs = build_template_spec(template_path)

    issues: List[str] = []
    for target in targets:
        lines = target.read_text(encoding="utf-8").splitlines()
        issues.extend(check_document_controls(target, lines))
        issues.extend(validate_sections(target, template_specs, lines))

    if issues:
        for issue in issues:
            print(issue)
        return 1

    print("All service specifications comply with the template.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
