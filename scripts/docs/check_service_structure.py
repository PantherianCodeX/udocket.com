#!/usr/bin/env python3
"""
Validate service specifications against the canonical template.

The script inspects numbered sections (## 1), ### 4.1, #### 8.3.1, …) and
verifies that:
  * Every section/sub-section defined in `_template.md` exists in the target
    document and appears in the same order.
  * Each section’s preamble block contains the required entries (Purpose,
    Contract, State, …) in the exact order declared by the template.

It reports concise, actionable errors:
    docs/src/services/llm-registry.md: Section 4.2 – missing preamble entry 'Breadcrumbs'

Usage examples:
    python scripts/docs/check_service_structure.py
    python scripts/docs/check_service_structure.py docs/src/services
    python scripts/docs/check_service_structure.py docs/src/services/llm-registry.md

Exit status is non-zero when any issue is found.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence, Tuple


HEADING_RE = re.compile(r"^(#{2,6})\s+(.*)")
TEMPLATE_NAME = "_template.md"
PREAMBLE_ENTRY_RE = re.compile(r"^\*\*(.+?):\*\*")


@dataclass(frozen=True)
class SectionSpec:
    numbering: Tuple[int, ...]
    level: int
    title: str
    preamble_order: Tuple[str, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate service docs against _template.md")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path("docs/src/services")],
        help="Service spec files or directories to validate (defaults to docs/src/services)",
    )
    return parser.parse_args()


def find_template(start: Path) -> Path:
    current = start if start.is_dir() else start.parent
    visited = set()
    while current not in visited:
        visited.add(current)
        candidate = current / TEMPLATE_NAME
        if candidate.is_file():
            return candidate
        current = current.parent
    # Fallback: common repo layout (docs/src/services/_template.md)
    alt = start if start.is_dir() else start.parent
    candidate = alt / "docs" / "src" / "services" / TEMPLATE_NAME
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(f"Could not locate {TEMPLATE_NAME} starting from {start}")


def parse_sections(markdown: str) -> List[Tuple[Tuple[int, ...], int, str, int]]:
    """Return list of (numbering tuple, level, title, line_number) for headings with numeric prefixes."""
    sections: List[Tuple[Tuple[int, ...], int, str, int]] = []
    lines = markdown.splitlines()
    for idx, line in enumerate(lines, start=1):
        match = HEADING_RE.match(line)
        if not match:
            continue
        hashes, title = match.groups()
        numbering = extract_numbering(title)
        if numbering is None:
            continue
        sections.append((numbering, len(hashes), title.strip(), idx))
    return sections


def extract_numbering(title: str) -> Tuple[int, ...] | None:
    title = title.strip()
    if m := re.match(r"^(\d+)\)", title):
        return (int(m.group(1)),)
    if m := re.match(r"^(\d+(?:\.\d+)+)", title):
        return tuple(int(part) for part in m.group(1).split("."))
    return None


def gather_preamble(lines: Sequence[str], start_idx: int) -> Tuple[str, ...]:
    entries: List[str] = []
    for line in lines[start_idx:]:
        if not line:
            continue
        match = PREAMBLE_ENTRY_RE.match(line)
        if match:
            entries.append(match.group(1).strip())
            continue
        # stop when we hit a non-preamble line (e.g., bullet, heading, blockquote)
        if not line.startswith("**"):
            break
    return tuple(entries)


def build_template_spec(template_path: Path) -> List[SectionSpec]:
    content = template_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    sections_meta = parse_sections(content)
    specs: List[SectionSpec] = []
    for numbering, level, title, line_no in sections_meta:
        preamble = gather_preamble(lines, line_no)
        specs.append(SectionSpec(numbering, level, title, preamble))
    return specs


def build_document_index(path: Path) -> Tuple[List[Tuple[Tuple[int, ...], int, str, int]], List[str]]:
    content = path.read_text(encoding="utf-8")
    sections = parse_sections(content)
    lines = content.splitlines()
    return sections, lines


def validate_file(path: Path, template_specs: List[SectionSpec], lines: Sequence[str]) -> List[str]:
    errors: List[str] = []
    doc_sections, _ = build_document_index(path)
    doc_map = {sec[0]: sec for sec in doc_sections}

    last_position = -1
    numbering_positions = {sec[0]: idx for idx, sec in enumerate(doc_sections)}

    for spec in template_specs:
        numbering = spec.numbering
        human_number = ".".join(str(n) for n in numbering)

        if numbering not in doc_map:
            errors.append(f"{path}: missing section {human_number}")
            continue

        position = numbering_positions[numbering]
        if position <= last_position:
            errors.append(f"{path}: section {human_number} out of order")
        last_position = position

        _, _, title, line_no = doc_map[numbering]
        preamble = gather_preamble(lines, line_no)

        if spec.preamble_order:
            if not preamble:
                errors.append(f"{path}: section {human_number} missing preamble block")
                continue

            for idx, expected in enumerate(spec.preamble_order):
                if idx >= len(preamble):
                    errors.append(
                        f"{path}: section {human_number} missing preamble entry '{expected}'"
                    )
                    break
                actual = preamble[idx]
                if actual != expected:
                    errors.append(
                        f"{path}: section {human_number} expected preamble entry '{expected}' at position {idx + 1} but found '{actual}'"
                    )
                    break
            else:
                if len(preamble) > len(spec.preamble_order):
                    extra = ", ".join(preamble[len(spec.preamble_order) :])
                    errors.append(
                        f"{path}: section {human_number} has unexpected additional preamble entries: {extra}"
                    )
        else:
            if preamble:
                entries = ", ".join(preamble)
                errors.append(
                    f"{path}: section {human_number} should not have preamble entries but found: {entries}"
                )

    return errors


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
                if candidate not in seen:
                    seen.add(candidate)
                    yield candidate
        else:
            norm = path.resolve()
            if norm.name == TEMPLATE_NAME:
                continue
            if norm not in seen:
                seen.add(norm)
                yield norm


def main() -> int:
    args = parse_args()
    targets = list(walk_targets(args.paths))
    if not targets:
        print("No markdown targets found.", file=sys.stderr)
        return 1

    template_path = find_template(args.paths[0].resolve())
    template_specs = build_template_spec(template_path)
    template_specs.sort(key=lambda spec: spec.numbering)

    issues: List[str] = []
    for target in targets:
        sections, lines = build_document_index(target)
        if not sections:
            continue
        issues.extend(validate_file(target, template_specs, lines))

    if issues:
        for issue in issues:
            print(issue)
        return 1

    print("All service specifications comply with the template.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

