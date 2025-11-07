#!/usr/bin/env python3
"""Generate the TDD SLO index appendix."""

from __future__ import annotations

import argparse
import os
import sys
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from doc_tools import paths
from doc_tools.doc_utils import (
    auto_generated_header,
    begin_auto_generated_marker,
    derive_doc_label,
    end_auto_generated_marker,
    parse_front_matter,
    read_markdown_lines,
    replace_auto_generated_section,
    stringify,
    write_or_check,
)
DOCS_DIR = paths.DOCS_ROOT
APPENDIX_FILE = DOCS_DIR / "overview" / "tdd" / "appendices" / "slo_index.md"
APPENDIX_DIR = APPENDIX_FILE.parent
MARKER_LABEL = "slo-index"
BEGIN_MARKER = begin_auto_generated_marker(MARKER_LABEL)
END_MARKER = end_auto_generated_marker(MARKER_LABEL)

SLO_HEADING_RE = re.compile(r"^###\s+6\.1\s+SLOs?\s*&\s*Targets.*$", re.IGNORECASE)
HEADINGS_RE = re.compile(r"^#{2,}\s")


@dataclass
class SLOEntry:
    doc_path: Path
    display_name: str
    content: list[str]


def derive_display_name(path: Path) -> str:
    lines = read_markdown_lines(path)
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    front = parse_front_matter(lines[start:])
    title = stringify(front.get("title", ""))
    fallback = path.relative_to(DOCS_DIR).as_posix()
    return derive_doc_label(title, fallback=fallback)


def extract_slo_section(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    capture: list[str] = []
    recording = False
    for line in lines:
        stripped = line.strip()
        if not recording:
            if SLO_HEADING_RE.match(stripped):
                recording = True
            continue
        if HEADINGS_RE.match(line):
            break
        capture.append(line.rstrip())

    while capture and not capture[0].strip():
        capture.pop(0)
    while capture and not capture[-1].strip():
        capture.pop()
    return capture


def collect_entries() -> list[SLOEntry]:
    entries: list[SLOEntry] = []
    doc_paths: list[Path] = []
    for root_path in paths.SERVICE_ROOTS:
        if not root_path.exists():
            continue
        doc_paths.extend(sorted(root_path.glob("*.md")))

    for doc_path in doc_paths:
        if doc_path.name.startswith("_template"):
            continue
        content = extract_slo_section(doc_path)
        if not content:
            continue
        entries.append(
            SLOEntry(
                doc_path=doc_path,
                display_name=derive_display_name(doc_path),
                content=content,
            )
        )

    entries.sort(key=lambda e: e.display_name.lower())
    return entries


def rel_from_appendix(target: Path) -> str:
    return Path(os.path.relpath(target, APPENDIX_DIR)).as_posix()


def render(entries: Sequence[SLOEntry]) -> str:
    lines: list[str] = []
    lines.extend(auto_generated_header(refresh_command="make docs.sync.slo"))
    if not entries:
        lines.append("_No SLO sections detected._")
        lines.append("")
        return "\n".join(lines)

    for entry in entries:
        doc_rel = rel_from_appendix(entry.doc_path)
        lines.append(f"### [{entry.display_name}]({doc_rel})")
        lines.append("")
        if entry.content:
            lines.extend(entry.content)
        else:
            lines.append("_No SLOs documented._")
        lines.append("")
    return "\n".join(lines)


def build_content() -> str:
    appendix_text = APPENDIX_FILE.read_text(encoding="utf-8")
    entries = collect_entries()
    generated = render(entries)
    return replace_auto_generated_section(appendix_text, MARKER_LABEL, generated)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify SLO index is up to date")
    args = parser.parse_args(argv)

    content = build_content()
    ok = write_or_check(
        APPENDIX_FILE,
        content,
        check=args.check,
        stale_message="SLO index is stale; run `make docs.sync.slo`.",
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
