#!/usr/bin/env python3
"""Generate the TDD API error codes index appendix."""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
SRC_DIR = ROOT / "docs" / "src"
APPENDIX_FILE = SRC_DIR / "overview" / "tdd" / "appendices" / "api_error_codes.md"
APPENDIX_DIR = APPENDIX_FILE.parent
BEGIN_MARKER = "<!-- BEGIN AUTO-GENERATED API ERROR INDEX -->"
END_MARKER = "<!-- END AUTO-GENERATED API ERROR INDEX -->"

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from scripts.docs.doc_utils import (  # noqa: E402
    read_markdown_lines,
    parse_front_matter,
    derive_doc_label,
    stringify,
    replace_marked_section,
) 

API_SECTION_RE = re.compile(r"^###\s+3\.3\s+API\s+error\s+codes.*$", re.IGNORECASE)
HEADINGS_RE = re.compile(r"^#{2,}\s")
LINK_PATTERN = re.compile(r"(\[[^\]]+\])\(([^)]+)\)")


@dataclass
class ApiSection:
    doc_path: Path
    display_name: str
    content: list[str]


def derive_display_name(path: Path) -> str:
    lines = read_markdown_lines(path)
    front = parse_front_matter(lines)
    title = stringify(front.get("title", ""))
    fallback = path.relative_to(SRC_DIR).as_posix()
    return derive_doc_label(title, fallback=fallback)


def extract_api_section(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    capture: list[str] = []
    recording = False
    for line in lines:
        if not recording:
            if API_SECTION_RE.match(line.strip()):
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


def adjust_relative_links(lines: list[str], doc_path: Path) -> list[str]:
    adjusted: list[str] = []

    for line in lines:
        def _replace(match: re.Match[str]) -> str:
            label, target = match.groups()
            if not target or target.startswith(("http://", "https://", "#", "mailto:", "data:")):
                return match.group(0)
            anchor = ""
            base = target
            if "#" in target:
                base, anchor = target.split("#", 1)
            resolved = (doc_path.parent / base).resolve()
            try:
                relative = Path(os.path.relpath(resolved, APPENDIX_DIR)).as_posix()
            except ValueError:
                return match.group(0)
            new_target = relative
            if anchor:
                new_target = f"{new_target}#{anchor}"
            return f"{label}({new_target})"

        adjusted.append(LINK_PATTERN.sub(_replace, line))
    return adjusted


def collect_entries() -> list[ApiSection]:
    entries: list[ApiSection] = []
    doc_paths: list[Path] = []
    doc_paths.extend(sorted((SRC_DIR / "services").glob("*.md")))
    doc_paths.extend(sorted((SRC_DIR / "apps").glob("*.md")))

    for doc_path in doc_paths:
        if doc_path.name.startswith("_template"):
            continue
        content = extract_api_section(doc_path)
        if not content:
            continue
        content = adjust_relative_links(content, doc_path)
        entries.append(
            ApiSection(
                doc_path=doc_path,
                display_name=derive_display_name(doc_path),
                content=content,
            )
        )

    entries.sort(key=lambda entry: entry.display_name.lower())
    return entries


def rel_from_appendix(target: Path) -> str:
    return Path(os.path.relpath(target, APPENDIX_DIR)).as_posix()


def render(entries: Sequence[ApiSection]) -> str:
    lines: list[str] = []
    lines.append("<!-- AUTO-GENERATED: Run `python scripts/docs/build_api_error_index.py` to refresh. -->")
    lines.append("")
    if not entries:
        lines.append("_No API error code sections detected._")
        lines.append("")
        return "\n".join(lines)

    for entry in entries:
        doc_rel = rel_from_appendix(entry.doc_path)
        lines.append(f"### [{entry.display_name}]({doc_rel})")
        lines.append("")
        if entry.content:
            lines.extend(entry.content)
        else:
            lines.append("_No API error codes documented._")
        lines.append("")
    return "\n".join(lines)


def build_content() -> str:
    appendix_text = APPENDIX_FILE.read_text(encoding="utf-8")
    entries = collect_entries()
    generated = render(entries)
    return replace_marked_section(appendix_text, BEGIN_MARKER, END_MARKER, generated)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify API error index is up to date")
    args = parser.parse_args(argv)

    content = build_content()
    if args.check:
        current = APPENDIX_FILE.read_text(encoding="utf-8")
        if content == current:
            return 0
        print("API error index is stale; run `python scripts/docs/build_api_error_index.py`.", file=sys.stderr)
        return 1

    APPENDIX_FILE.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
