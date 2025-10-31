#!/usr/bin/env python3
"""Generate the consolidated runbook catalog from service design documents."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from scripts.docs.doc_utils import (  # noqa: E402
    begin_auto_generated_marker,
    derive_doc_label,
    end_auto_generated_marker,
    parse_front_matter,
    slugify,
    stringify,
    write_or_check,
)

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "docs" / "src"
OUTPUT_FILE = SRC_DIR / "ops" / "runbooks.md"
MARKER_LABEL = "runbook-catalog"
BEGIN_MARKER = begin_auto_generated_marker(MARKER_LABEL)
END_MARKER = end_auto_generated_marker(MARKER_LABEL)

FRONT_MATTER = """---
title: "uDocket — Ops Appendix: Runbook Catalog"
subtitle: "Aggregated runbooks and drill references"
authors:
  - "Platform Operations Team"
version: "0.1-draft"
status: implementable
classification: Confidential
last_updated: "2025-10-30"
updated_by: "Documentation Team"
owners:
  - "Platform Operations Team"
reviewers:
  - "Platform Operations Team"
approvers:
  - "Operations Steering Committee"
approved_by:
approved_date:
---"""

DOCUMENT_CONTROLS_TABLE = """## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Platform Operations Team |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-30 |
| Updated by | Documentation Team |
| Owners | Platform Operations Team |
| Reviewers | Platform Operations Team |
| Approvers | Operations Steering Committee |
| Approved by |  |
| Approved date |  |
<!-- END AUTO-GENERATED: document-controls -->"""

APPENDIX_OVERVIEW = """## Appendix Overview

This appendix consolidates runbook sections from service and application specifications. Refresh it with `python scripts/docs/build_runbook_catalog.py`. The content between the markers below is generated automatically."""

RUNBOOK_HEADING_RE = re.compile(r"^(#{2,6})\s+.*runbook", re.IGNORECASE)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")
RB_ID_RE = re.compile(r"(RB-[A-Z0-9-]+)")


@dataclass
class Heading:
    level: int
    text: str
    slug: str


def iter_source_files() -> Iterable[Path]:
    """Yield component documentation files that may contain runbook sections."""

    roots = [SRC_DIR / "services", SRC_DIR / "apps"]
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.glob("*.md")):
            if path.name.startswith("_template"):
                continue
            if path in seen:
                continue
            seen.add(path)
            yield path


def read_doc_label(lines: Sequence[str], path: Path) -> str:
    """Return a short label derived from the document title/front matter."""

    front = parse_front_matter(lines)
    if front:
        title = stringify(front.get("title", ""))
    else:
        title = ""

    fallback = path.stem.replace("tdd-", "").replace("-", " ").title()
    return derive_doc_label(title, fallback=fallback)


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
    pending_blank_after_heading = False
    anchors_added: set[str] = set()

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
                anchor_id = anchor.group(1).lower()
                if anchor_id not in anchors_added:
                    if output and output[-1].strip():
                        output.append("")
                    output.append(f'<a id="{anchor_id}"></a>')
                    anchors_added.add(anchor_id)
            if output and output[-1].strip():
                output.append("")
            slug = slugify(prefixed_text)
            heading_line = f"{'#' * normalized_level} {prefixed_text}"
            if slug:
                heading_line += f" {{#{slug}}}"
            output.append(heading_line)
            pending_blank_after_heading = True
            headings.append(
                Heading(level=normalized_level, text=prefixed_text, slug=slugify(prefixed_text))
            )
        else:
            if pending_blank_after_heading:
                if line.strip():
                    output.append("")
                pending_blank_after_heading = False
            matches = RB_ID_RE.findall(line)
            stripped = line.lstrip()
            if matches and stripped.startswith("|"):
                output.append(line)
                continue
            if matches and any(stripped.startswith(prefix) for prefix in ("- ", "* ", "+ ")):
                prefix_len = len(line) - len(stripped)
                marker = stripped[:2]
                remainder = stripped[2:]
                anchor_html = ""
                for match in matches:
                    anchor_id = match.lower()
                    if anchor_id not in anchors_added:
                        anchor_html += f'<a id="{anchor_id}"></a>'
                        anchors_added.add(anchor_id)
                output.append(f"{line[:prefix_len]}{marker}{anchor_html}{remainder}")
                continue
            if matches:
                for match in matches:
                    anchor_id = match.lower()
                    if anchor_id not in anchors_added:
                        output.append(f'<a id="{anchor_id}"></a>')
                        anchors_added.add(anchor_id)
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
    lines.extend(FRONT_MATTER.splitlines())
    lines.append("")
    lines.append("______________________________________________________________________")
    lines.append("")
    lines.extend(DOCUMENT_CONTROLS_TABLE.splitlines())
    lines.append("")
    lines.append("______________________________________________________________________")
    lines.append("")
    lines.extend(APPENDIX_OVERVIEW.splitlines())
    lines.append("")
    lines.append("______________________________________________________________________")
    lines.append("")
    lines.append(BEGIN_MARKER)
    lines.append("<!-- AUTO-GENERATED: Run `python scripts/docs/build_runbook_catalog.py` to refresh. -->")
    lines.append("")
    if catalog_lines:
        lines.extend(catalog_lines)
    else:
        lines.append("_No runbook sections detected._")
        lines.append("")
    lines.append(END_MARKER)
    lines.append("")
    return "\n".join(lines)


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
        ok = write_or_check(
            OUTPUT_FILE,
            content,
            check=True,
            stale_message="Runbook catalog is stale. Run build_runbook_catalog.py to refresh.",
        )
        return 0 if ok else 1

    write_or_check(OUTPUT_FILE, content, check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
