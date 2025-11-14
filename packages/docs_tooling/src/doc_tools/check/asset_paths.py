from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable, Iterator

from doc_tools.config import paths


IMG_HTML_RE = re.compile(r"<img[^>]*\bsrc=[\"']([^\"']+)[\"']", re.IGNORECASE)
IMG_MARKDOWN_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "data:", "mailto:", "tel:")


@dataclass
class AssetReference:
    path: Path
    line: int
    target: str


def _normalise_target(target: str) -> str:
    value = target.strip()
    if not value:
        return value
    for sep in ("#", "?"):
        if sep in value:
            value = value.split(sep, 1)[0]
    return value.strip()


def _is_relative_reference(target: str) -> bool:
    if not target:
        return False
    if target.startswith(SKIP_PREFIXES):
        return False
    if target.startswith(("#", "//")):
        return False
    if "://" in target.split("/", 1)[0]:
        return False
    return True


def _iter_asset_targets(text: str) -> Iterator[tuple[int, str]]:
    for idx, line in enumerate(text.splitlines(), 1):
        for match in IMG_HTML_RE.finditer(line):
            yield idx, match.group(1)
        for match in IMG_MARKDOWN_RE.finditer(line):
            yield idx, match.group(1)


def _within_docs_root(candidate: Path, docs_root: Path) -> bool:
    try:
        candidate.relative_to(docs_root)
    except ValueError:
        return False
    return True


def collect_asset_references(path: Path) -> list[AssetReference]:
    text = path.read_text(encoding="utf-8")
    refs: list[AssetReference] = []
    for line, target in _iter_asset_targets(text):
        cleaned = _normalise_target(target)
        if not _is_relative_reference(cleaned):
            continue
        refs.append(AssetReference(path=path, line=line, target=cleaned))
    return refs


def validate_reference(ref: AssetReference, docs_root: Path) -> str | None:
    candidate = (ref.path.parent / ref.target).resolve(strict=False)
    if not _within_docs_root(candidate, docs_root):
        return (
            f"{ref.path.relative_to(paths.REPO_ROOT)}:{ref.line}: embedded asset '{ref.target}' "
            f"resolves outside docs/ (-> {candidate})"
        )
    return None


def check_paths(targets: Iterable[Path]) -> list[str]:
    docs_root = paths.DOCS_ROOT.resolve()
    issues: list[str] = []
    for path in targets:
        for ref in collect_asset_references(path):
            problem = validate_reference(ref, docs_root)
            if problem:
                issues.append(problem)
    return issues


def gather_targets(inputs: Iterable[Path]) -> list[Path]:
    collected: list[Path] = []
    for entry in inputs:
        if entry.is_dir():
            root = entry.resolve()
            collected.extend(sorted(root.rglob("*.md")))
        elif entry.suffix.lower() == ".md" and entry.exists():
            collected.append(entry.resolve())
    return collected


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate embedded asset paths remain within the docs tree.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=None,
        help="Markdown files or directories to validate (defaults to docs/ tree)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.paths:
        targets = gather_targets(args.paths)
    else:
        targets = gather_targets([paths.DOCS_ROOT])

    issues = check_paths(targets)
    if issues:
        print("Embedded asset path issues detected:")
        for issue in issues:
            print(f" - {issue}")
        return 1
    print("Embedded asset paths validated successfully.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
