#!/usr/bin/env python3
"""Ensure Document Controls tables use managed auto-generated markers."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from doc_tools.config import paths
from doc_tools.common.doc_utils import begin_auto_generated_marker, end_auto_generated_marker

DEFAULT_TARGETS: tuple[Path, ...] = (paths.DOCS_ROOT,)
DOCUMENT_CONTROLS_LABEL = "document-controls"
DOCUMENT_CONTROLS_HEADING = "## document controls"
BEGIN_MARKER = begin_auto_generated_marker(DOCUMENT_CONTROLS_LABEL)
END_MARKER = end_auto_generated_marker(DOCUMENT_CONTROLS_LABEL)


@dataclass(frozen=True)
class MarkerIssue:
    path: Path
    detail: str

    def format(self) -> str:
        return f"{self.path}: {self.detail}"


def normalize_path(entry: str) -> Path:
    path = Path(entry)
    if not path.is_absolute():
        path = paths.REPO_ROOT / path
    return path


def iter_markdown_targets(raw_targets: Iterable[Path]) -> Iterator[Path]:
    seen: set[Path] = set()
    for target in raw_targets:
        if not target.exists():
            print(f"[doc-controls-tags] warning: {target} does not exist; skipping", file=sys.stderr)
            continue
        if target.is_dir():
            for candidate in sorted(target.rglob("*.md")):
                resolved = candidate.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield resolved
            continue
        if target.suffix.lower() != ".md":
            continue
        resolved = target.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        yield resolved


def has_document_controls_heading(lines: Sequence[str]) -> bool:
    for line in lines:
        if line.strip().lower() == DOCUMENT_CONTROLS_HEADING:
            return True
    return False


def check_file(path: Path) -> list[MarkerIssue]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not has_document_controls_heading(lines):
        return []

    issues: list[MarkerIssue] = []
    if BEGIN_MARKER not in text:
        issues.append(MarkerIssue(path, f"missing '{BEGIN_MARKER}' marker"))
    if END_MARKER not in text:
        issues.append(MarkerIssue(path, f"missing '{END_MARKER}' marker"))
    return issues


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify Document Controls tables include auto-generated begin/end markers."
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="Optional Markdown files or directories to scan (defaults to docs/).",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    target_args = [normalize_path(entry) for entry in args.targets] if args.targets else list(DEFAULT_TARGETS)
    markdown_targets = list(iter_markdown_targets(target_args))
    if not markdown_targets:
        print("[doc-controls-tags] no markdown targets to scan.", file=sys.stderr)
        return 0

    issues: list[MarkerIssue] = []
    for path in markdown_targets:
        issues.extend(check_file(path))

    if issues:
        print("Document Controls marker issues detected:")
        for issue in issues:
            print(f" - {issue.format()}")
        return 1

    print("All Document Controls tables include auto-generated markers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
