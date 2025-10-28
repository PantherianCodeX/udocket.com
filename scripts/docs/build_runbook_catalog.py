#!/usr/bin/env python3
"""Generate the consolidated runbook catalog from service design documents."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "docs" / "src"
OUTPUT_FILE = SRC_DIR / "ops" / "runbooks" / "index.md"

RUNBOOK_HEADING_RE = re.compile(r"^(#{2,6})\s+.*runbook", re.IGNORECASE)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")
RB_ID_RE = re.compile(r"(RB-[A-Z0-9-]+)")


@dataclass
class Heading:
    level: int
    text: str
    slug: str


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return slug.strip("-")


def iter_source_files() -> Iterable[Path]:
    """Yield component documentation files that may contain runbook sections."""

    roots = [SRC_DIR / "services", SRC_DIR / "apps"]
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.glob("*.md")):
            if path in seen:
                continue
            seen.add(path)
            yield path


def read_doc_label(lines: Sequence[str], path: Path) -> str:
    """Return a short label derived from the document title/front matter."""

    title_pattern = re.compile(r'title:\s*"([^"]+)"')
    for line in lines[:40]:
        match = title_pattern.search(line)
        if not match:
            continue
        raw = match.group(1)
        if "—" in raw:
            raw = raw.split("—", 1)[1].strip()
        raw = raw.replace("Technical Design", "").replace("Specification", "")
        raw = raw.replace("Technical Architecture", "").replace("Overview", "")
        raw = re.sub(r"\s+", " ", raw).strip(" -–—")
        if raw:
            return raw

    stem = path.stem.replace("tdd-", "").replace("-", " ")
    return stem.title()


def extract_runbook_sections(lines: Sequence[str]) -> list[list[str]]:
    sections: list[list[str]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        match = RUNBOOK_HEADING_RE.match(line)
        if match:
            level = len(match.group(1))
            start = i
            i += 1
            while i < len(lines):
                next_line = lines[i]
                heading_match = HEADING_RE.match(next_line)
                if heading_match:
                    next_level = len(heading_match.group(1))
                    if next_level <= level:
                        break
                i += 1
            sections.append(list(lines[start:i]))
        else:
            i += 1
    return sections


def transform_section(section: list[str], label: str, path: Path) -> tuple[list[str], list[Heading]]:
    output: list[str] = []
    headings: list[Heading] = []
    first_heading = True

    level_adjust = 0
    for line in section:
        heading_match = HEADING_RE.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            if first_heading and level < 2:
                raise ValueError(
                    f"Runbook sections must begin with an H2 or deeper heading in {path.name}: '{text}'."
                )
            if first_heading:
                if level > 2:
                    level_adjust = level - 2
                first_heading = False

            normalized_level = max(2, level - level_adjust)

            prefixed_text = f"{label} — {text}"
            anchor = RB_ID_RE.search(text)
            if anchor:
                if output and output[-1].strip():
                    output.append("")
                output.append(f'<a id="{anchor.group(1).lower()}"></a>')
            if output and output[-1].strip():
                output.append("")
            output.append(f"{'#' * normalized_level} {prefixed_text}")
            headings.append(
                Heading(level=normalized_level, text=prefixed_text, slug=slugify(prefixed_text))
            )
        else:
            output.append(line)

    while output and not output[-1].strip():
        output.pop()
    output.append("")
    return output, headings


def build_catalog() -> tuple[list[str], list[Heading]]:
    catalog_lines: list[str] = []
    toc_headings: list[Heading] = []

    for path in iter_source_files():
        lines = path.read_text(encoding="utf-8").splitlines()
        sections = extract_runbook_sections(lines)
        if not sections:
            continue
        label = read_doc_label(lines, path)
        for section in sections:
            if catalog_lines and catalog_lines[-1].strip():
                catalog_lines.append("")
            transformed, headings = transform_section(section, label, path)
            catalog_lines.extend(transformed)
            toc_headings.extend(headings)
    while catalog_lines and not catalog_lines[-1].strip():
        catalog_lines.pop()
    return catalog_lines, toc_headings


def render(catalog_lines: list[str]) -> str:
    lines: list[str] = []
    lines.append("# uDocket Runbook Catalog")
    lines.append("")
    lines.append("<!-- AUTO-GENERATED: Run `python scripts/docs/build_runbook_catalog.py` to refresh. -->")
    lines.append("")
    if not catalog_lines:
        lines.append("_No runbook sections detected._")
        lines.append("")
        return "\n".join(lines) + "\n"

    lines.extend(catalog_lines)
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Verify the catalog is up to date")
    args = parser.parse_args(argv)

    catalog_lines, _ = build_catalog()
    content = render(catalog_lines)

    if args.check:
        if not OUTPUT_FILE.exists():
            print("Runbook catalog is missing; regenerate it.", file=sys.stderr)
            return 1
        current = OUTPUT_FILE.read_text(encoding="utf-8")
        if current != content:
            print("Runbook catalog is stale. Run build_runbook_catalog.py to refresh.", file=sys.stderr)
            return 1
        return 0

    OUTPUT_FILE.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
