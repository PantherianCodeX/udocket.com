#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "src" / "overview" / "tdd.md"

def find_diagram_refs(text: str) -> set[str]:
    # Diagrams live alongside their owning documents (overview/tdd or service/app directories).
    pattern = r"docs/src/(?:overview/tdd|services/[^/]+|apps/[^/]+)/diagrams/[\w\-/]+\.mmd"
    return set(re.findall(pattern, text))

def check_diagrams(text: str) -> list[str]:
    problems: list[str] = []
    for ref in sorted(find_diagram_refs(text)):
        p = ROOT / ref
        if not p.exists():
            problems.append(f"Missing diagram source: {ref}")
    return problems

def find_appendix_refs(text: str) -> set[str]:
    return set(re.findall(r"App\.([A-Z])", text))

def find_appendix_defs(text: str) -> set[str]:
    heads = set()
    for line in text.splitlines():
        m = re.match(r"^##\s+Appendix\s+([A-Z])\b", line.strip())
        if m:
            heads.add(m.group(1))
    return heads

def check_appendices(text: str) -> list[str]:
    refs = find_appendix_refs(text)
    defs = find_appendix_defs(text)
    # Allow certain appendices to live in external appendix pages (e.g., Glossary App.I)
    external_ok = {"I"}
    missing = {x for x in refs if x not in defs and x not in external_ok}
    if missing:
        return [f"Appendix referenced but not defined in TDD: App.{x}" for x in sorted(missing)]
    return []

def find_section_defs(text: str) -> set[str]:
    nums = set()
    for line in text.splitlines():
        m = re.match(r"^##\s+(\d+)\)\s+", line.strip())
        if m:
            nums.add(m.group(1))
    return nums

def find_section_refs(text: str) -> set[str]:
    # Collect major section numbers from §x or §x.y references
    majors: set[str] = set()
    for m in re.findall(r"§(\d+)(?:\.\d+)?", text):
        majors.add(m)
    return majors

def check_sections(text: str) -> list[str]:
    defs = find_section_defs(text)
    if not defs:
        return []
    max_defined = max(int(x) for x in defs)
    problems: list[str] = []
    for ref in find_section_refs(text):
        try:
            num = int(ref)
        except ValueError:
            continue
        if num >= 100:
            # Likely referencing external regulations (e.g., HIPAA §164).
            continue
        if num <= max_defined and ref not in defs:
            problems.append(f"Section referenced but missing major heading: §{ref})")
    return problems

def main() -> int:
    if not DOC.exists():
        print(f"Cannot find {DOC}")
        return 2
    text = DOC.read_text(encoding="utf-8")
    problems: list[str] = []
    problems += check_diagrams(text)
    problems += check_appendices(text)
    problems += check_sections(text)
    if problems:
        print("Doc link/check issues:")
        for p in problems:
            print(f" - {p}")
        strict = os.getenv("STRICT_DOCS", "0").lower() in {"1","true","yes"}
        return 1 if strict else 0
    print("Docs check passed: diagrams present, appendices and sections referenced are defined.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
