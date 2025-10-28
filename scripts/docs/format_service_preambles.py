#!/usr/bin/env python3
"""Normalize service specification preamble blocks to match the template.

The formatter rewrites preamble entries so they:
* Appear in the same order as `_template.md`.
* Include every required entry (missing items are filled using template text).
* End with `**|**` for consistency.
* Avoid preamble entries where the template expects none (labels are converted to
  plain text in that case).

Usage examples:
    python scripts/docs/format_service_preambles.py              # rewrite all services
    python scripts/docs/format_service_preambles.py docs/src/services/web-app.md
    python scripts/docs/format_service_preambles.py --template docs/custom_template.md

The script rewrites files in place. Commit before running if you want the option
to revert easily.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Sequence, Tuple

TEMPLATE_NAME = "_template.md"
HEADING_RE = re.compile(r"^(#{2,6})\s+(.*)")
PREAMBLE_RE = re.compile(r"^\*\*(.+?):\*\*\s*(.*)$")

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
    preamble_defaults: Dict[str, str]
    preamble_requires_marker: Dict[str, bool]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Format service doc preambles using the canonical template")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path("docs/src/services")],
        help="Markdown files or directories to rewrite (defaults to docs/src/services)",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=None,
        help="Override path to _template.md (defaults to nearest ancestor)"
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
        hashes, title = m.groups()
        numbering = extract_numbering(title)
        if numbering is None:
            continue
        sections.append((numbering, len(hashes), title.strip(), idx))
    return sections


def gather_preamble(lines: Sequence[str], start_idx: int) -> Tuple[List[str], List[Tuple[int, str, str]]]:
    blanks: List[str] = []
    entries: List[Tuple[int, str, str]] = []
    idx = start_idx
    length = len(lines)
    while idx < length:
        line = lines[idx]
        stripped = line.strip()
        if not stripped:
            blanks.append(line)
            idx += 1
            continue
        m = PREAMBLE_RE.match(stripped)
        if not m:
            break
        label = LABEL_NORMALISATION.get(m.group(1).lower(), m.group(1))
        body = m.group(2)
        entries.append((idx, label, body))
        idx += 1
    return blanks, entries


def build_template_spec(template_path: Path) -> Dict[Tuple[int, ...], SectionSpec]:
    content = template_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    specs: Dict[Tuple[int, ...], SectionSpec] = {}
    for numbering, level, title, line_no in parse_sections(content):
        blanks, entries = gather_preamble(lines, line_no)
        order: List[str] = []
        defaults: Dict[str, str] = {}
        marker_map: Dict[str, bool] = {}
        for _, label, body in entries:
            body_stripped = body.strip()
            has_marker = body_stripped.endswith("**|**")
            marker_map[label] = has_marker
            if has_marker:
                body_stripped = body_stripped[:-4].rstrip()
            order.append(label)
            defaults[label] = body_stripped
        specs[numbering] = SectionSpec(numbering, level, title, tuple(order), defaults, marker_map)
    return specs


def walk_targets(paths: Iterable[Path]) -> Iterator[Path]:
    seen: set[Path] = set()
    for path in paths:
        if not path.exists():
            print(f"warning: {path} does not exist; skipping")
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


def normalise_body(text: str, requires_marker: bool) -> str:
    cleaned = text.strip()
    if requires_marker:
        if not cleaned.endswith("**|**"):
            cleaned = cleaned.rstrip('* ') + " **|**"
    else:
        if cleaned.endswith("**|**"):
            cleaned = cleaned[:-4].rstrip()
    return cleaned


def strip_marker(text: str) -> str:
    cleaned = text.strip()
    if cleaned.endswith("**|**"):
        cleaned = cleaned[:-4].rstrip()
    return cleaned


def format_file(path: Path, template_spec: Dict[Tuple[int, ...], SectionSpec]) -> None:
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines()
    sections = parse_sections(original)
    sections_map = {num: (idx, level, title) for num, level, title, idx in sections}

    offset = 0
    for numbering, spec in template_spec.items():
        if numbering not in sections_map:
            continue
        heading_idx = sections_map[numbering][0] - 1 + offset
        blank_lines, entries = gather_preamble(lines, heading_idx + 1)
        # indexes in entries correspond to original lines; we ignore now
        existing_map: Dict[str, str] = {}
        for _, label, body in entries:
            existing_map[label] = body.strip()
        replace_start = heading_idx + 1
        replace_end = replace_start + len(blank_lines) + len(entries)

        new_block: List[str] = []
        if spec.preamble_order:
            new_block.append("")
            for label in spec.preamble_order:
                body = existing_map.get(label)
                if body is None:
                    body = spec.preamble_defaults.get(label, "")
                requires_marker = spec.preamble_requires_marker.get(label, True)
                body = normalise_body(body, requires_marker)
                new_block.append(f"**{label}:** {body}")
        else:
            # Template expects no preamble; drop any existing entries entirely.
            new_block = []
        lines[replace_start:replace_end] = new_block
        offset += len(new_block) - (replace_end - replace_start)

        insert_idx = replace_start + len(new_block)
        if spec.preamble_order and insert_idx < len(lines) and lines[insert_idx].strip():
            lines.insert(insert_idx, "")
            offset += 1

    # Ensure every heading is followed by a blank line to satisfy markdownlint MD022/MD032.
    idx = 0
    while idx < len(lines) - 1:
        if HEADING_RE.match(lines[idx]):
            if lines[idx + 1].strip():
                lines.insert(idx + 1, "")
            idx += 1
        idx += 1

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    targets = list(walk_targets(args.paths))
    if not targets:
        print("No markdown targets found.")
        return
    template_path = find_template(targets[0], args.template)
    template_spec = build_template_spec(template_path)
    for target in targets:
        format_file(target, template_spec)
    print(f"Formatted {len(targets)} file(s) using template {template_path}.")


if __name__ == "__main__":  # pragma: no cover
    main()
