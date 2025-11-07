from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# headings that should be skipped entirely (rare)
SKIP_FILES: set[Path] = set()
TAG_WORDS = {"binding", "informative", "normative", "summary", "roadmap"}
HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.*?)(?:\s+\{#(?P<anchor>[A-Za-z0-9_.-]+)\})?\s*$")


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def normalise_title(raw: str) -> str:
    title = raw.strip()
    # drop trailing parenthetical tags like "(binding)" or "(roadmap, informative)"
    title = re.sub(r"\s*\([^)]*\)\s*$", "", title)
    # remove closing parenthesis immediately after digits (e.g., "3) API")
    title = re.sub(r"(?<=\d)\)(?=\s|$)", "", title)
    # collapse dotted section numbers (e.g., 2.1 -> 21)
    title = re.sub(r"(?<=\d)\.(?=\d)", "", title)
    return title.strip()


def check_file(path: Path) -> list[str]:
    issues: list[str] = []
    text = path.read_text(encoding="utf-8")
    for idx, line in enumerate(text.splitlines(), 1):
        match = HEADING_RE.match(line)
        if not match:
            continue
        anchor = match.group("anchor")
        if not anchor:
            continue
        if any(word in anchor for word in TAG_WORDS):
            issues.append(
                f"{path}:{idx}: anchor '#{anchor}' includes reserved tag keyword; headings must not encode binding/normative/summary markers."
            )
            continue
        expected = slugify(normalise_title(match.group("title")))
        if expected and anchor != expected:
            issues.append(
                f"{path}:{idx}: anchor '#{anchor}' does not match slug '{expected}' derived from heading '{match.group('title')}'."
            )
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify explicit heading anchors match slugified titles and omit tag keywords.")
    parser.add_argument("paths", nargs="+", type=Path, help="Markdown files to validate.")
    args = parser.parse_args(argv)

    problems: list[str] = []
    for path in args.paths:
        if path in SKIP_FILES:
            continue
        if not path.exists():
            problems.append(f"warning: {path} does not exist; skipping")
            continue
        problems.extend(check_file(path))

    if problems:
        print("Heading anchor issues detected:")
        for problem in problems:
            print(f" - {problem}")
        return 1
    print("Heading anchors validated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
