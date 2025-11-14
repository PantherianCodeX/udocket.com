"""Validate repository tree appendices against the live repo structure."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from collections.abc import Sequence

from doc_tools.config import paths

DEFAULT_APPENDIX = paths.DOCS_ROOT / "overview" / "tdd" / "appendices" / "repository_trees.md"


@dataclass(frozen=True)
class TreeEntry:
    rel_path: PurePosixPath
    is_dir: bool
    line: str


@dataclass(frozen=True)
class TreeBlock:
    section: str
    entries: tuple[TreeEntry, ...]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ensure the repository tree appendix stays aligned with the repository layout.",
    )
    parser.add_argument(
        "--appendix",
        type=Path,
        default=DEFAULT_APPENDIX,
        help="Path to repository_trees.md (defaults to docs/overview/tdd/appendices/repository_trees.md)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=paths.REPO_ROOT,
        help="Repository root used for validation (defaults to doc_tools.paths.REPO_ROOT)",
    )
    return parser.parse_args(list(argv or []))


def normalise_heading(raw: str) -> str:
    heading = raw.lstrip("#").strip()
    if "{" in heading:
        heading = heading.split("{", 1)[0].strip()
    return heading or "Appendix"


def extract_blocks(content: str) -> list[TreeBlock]:
    lines = content.splitlines()
    blocks: list[TreeBlock] = []
    current_section = "Appendix"
    collecting = False
    buffer: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### "):
            current_section = normalise_heading(stripped)
        if stripped.startswith("```tree"):
            collecting = True
            buffer = []
            continue
        if stripped.startswith("```") and collecting:
            entries = tuple(parse_tree_block(buffer))
            blocks.append(TreeBlock(section=current_section, entries=entries))
            buffer = []
            collecting = False
            continue
        if collecting:
            buffer.append(line.rstrip("\n"))
    return blocks


_TREE_ART_PREFIX = set("│├┤└┘┌┐┴┬┼╰╯╭╮─")
_COMMENT_SEPARATORS: tuple[str, ...] = (" - ", " — ")


def _strip_tree_art(token: str) -> str:
    cleaned = token
    while cleaned and cleaned[0] in _TREE_ART_PREFIX:
        cleaned = cleaned[1:]
        cleaned = cleaned.lstrip()
    return cleaned


def _strip_trailing_comment(token: str) -> str:
    for sep in _COMMENT_SEPARATORS:
        if sep in token:
            return token.split(sep, 1)[0].rstrip()
    return token


def _indent_count(line: str) -> int:
    expanded = line.replace("\t", "    ")
    indent_str = "".join(" " if ch in _TREE_ART_PREFIX else ch for ch in expanded)
    return len(indent_str) - len(indent_str.lstrip(" "))


def parse_tree_block(lines: Sequence[str]) -> list[TreeEntry]:
    raw_entries: list[tuple[int, str, bool, str]] = []
    for raw_line in lines:
        if not raw_line.strip():
            continue
        indent = _indent_count(raw_line)
        token = raw_line.strip()
        if not token or token.startswith("#"):
            continue
        token = _strip_tree_art(token)
        token = _strip_trailing_comment(token).strip()
        if not token:
            continue
        explicit_dir = token.endswith("/")
        label = token.rstrip("/")
        if not label:
            continue
        raw_entries.append((indent, label, explicit_dir, raw_line))

    entries: list[TreeEntry] = []
    stack: list[tuple[int, PurePosixPath]] = []
    for index, (indent, label, explicit_dir, original_line) in enumerate(raw_entries):
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1] if stack else None
        rel_path = PurePosixPath(label) if parent is None else parent / label
        next_indent = raw_entries[index + 1][0] if index + 1 < len(raw_entries) else -1
        has_children = next_indent > indent
        is_dir = explicit_dir or has_children
        entries.append(TreeEntry(rel_path=rel_path, is_dir=is_dir, line=original_line.strip()))
        if is_dir:
            stack.append((indent, rel_path))
    return entries


def _resolve_entry_path(repo_root: Path, rel_path: PurePosixPath) -> Path:
    parts = list(rel_path.parts)
    if parts and parts[0] == repo_root.name:
        parts = parts[1:]
    if not parts:
        return repo_root
    return repo_root.joinpath(*parts)


def validate_blocks(blocks: Sequence[TreeBlock], repo_root: Path) -> list[str]:
    issues: list[str] = []
    for block in blocks:
        for entry in block.entries:
            target = _resolve_entry_path(repo_root, entry.rel_path)
            if not target.exists():
                issues.append(
                    f"[repository-trees] missing path '{entry.rel_path}' in section '{block.section}'",
                )
                continue
            if entry.is_dir and not target.is_dir():
                issues.append(
                    f"[repository-trees] expected directory for '{entry.rel_path}' in section '{block.section}'",
                )
            if not entry.is_dir and target.is_dir():
                issues.append(
                    f"[repository-trees] expected file for '{entry.rel_path}' in section '{block.section}'",
                )
    return issues


def resolve_appendix(path: Path, repo_root: Path) -> Path:
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    appendix_path = resolve_appendix(args.appendix, repo_root)
    if not appendix_path.exists():
        print(f"[repository-trees] appendix not found at {appendix_path}", file=sys.stderr)
        return 2
    content = appendix_path.read_text(encoding="utf-8")
    blocks = extract_blocks(content)
    if not blocks:
        print(
            f"[repository-trees] no ```tree fenced blocks found in {appendix_path}",
            file=sys.stderr,
        )
        return 1
    issues = validate_blocks(blocks, repo_root)
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1
    print(f"[repository-trees] {appendix_path} is aligned with {repo_root}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
