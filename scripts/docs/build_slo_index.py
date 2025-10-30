#!/usr/bin/env python3
"""Generate the TDD SLO index appendix."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
import re

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
SRC_DIR = ROOT / "docs" / "src"
APPENDIX_FILE = SRC_DIR / "overview" / "tdd" / "appendices" / "slo_index.md"
APPENDIX_DIR = APPENDIX_FILE.parent
BEGIN_MARKER = "<!-- BEGIN AUTO-GENERATED SLO INDEX -->"
END_MARKER = "<!-- END AUTO-GENERATED SLO INDEX -->"

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from scripts.docs import doc_utils  # type: ignore  # noqa: E402

SLO_HEADING_RE = re.compile(r"^###\s+6\.1\s+SLOs?\s*&\s*Targets.*$", re.IGNORECASE)
HEADINGS_RE = re.compile(r"^#{2,}\s")


@dataclass
class SLOEntry:
    doc_path: Path
    display_name: str
    content: list[str]


def derive_display_name(path: Path) -> str:
    lines = doc_utils.read_markdown_lines(path)
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    front = doc_utils.parse_front_matter(lines[start:])
    title = doc_utils.stringify(front.get("title", ""))
    fallback = path.relative_to(SRC_DIR).as_posix()
    return doc_utils.derive_doc_label(title, fallback=fallback)


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
    doc_paths = []
    doc_paths.extend(sorted((SRC_DIR / "services").glob("*.md")))
    doc_paths.extend(sorted((SRC_DIR / "apps").glob("*.md")))

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
    lines.append("<!-- AUTO-GENERATED: Run `python scripts/docs/build_slo_index.py` to refresh. -->")
    lines.append("")
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
    return doc_utils.replace_marked_section(appendix_text, BEGIN_MARKER, END_MARKER, generated)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify SLO index is up to date")
    args = parser.parse_args(argv)

    content = build_content()
    if args.check:
        current = APPENDIX_FILE.read_text(encoding="utf-8")
        if content == current:
            return 0
        print("SLO index is stale; run `python scripts/docs/build_slo_index.py`.", file=sys.stderr)
        return 1

    APPENDIX_FILE.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
