from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

from doc_tools import paths
from doc_tools.doc_utils import derive_doc_label, parse_front_matter, read_markdown_lines, stringify

MKDOCS_CONFIG = paths.DOCS_PACKAGE_ROOT / "mkdocs.yml"
APPENDICES_DIR = paths.DOCS_ROOT / "overview" / "tdd" / "appendices"
SECTION_HEADER = "- Architecture Appendices:"
SECTION_INDENT = "  "
ITEM_INDENT = "    "


def discover_appendices(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.glob("*.md")
        if path.is_file() and not path.name.startswith("_")
    )


def _parse_label(path: Path) -> str:
    try:
        lines = read_markdown_lines(path)
    except OSError:
        return path.stem.replace("_", " ").title()
    front = parse_front_matter(lines)
    if not front:
        return path.stem.replace("_", " ").title()
    title = stringify(front.get("title", "")) or path.stem
    return derive_doc_label(title, fallback=path.stem)


def _collect_existing(lines: list[str], start: int, end: int) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for idx in range(start + 1, end):
        stripped = lines[idx].strip()
        if not stripped.startswith("- "):
            continue
        if ":" not in stripped:
            continue
        label, target = stripped[2:].split(":", 1)
        entries.append((label.strip(), target.strip()))
    return entries


def _find_section(lines: list[str]) -> tuple[int, int]:
    start = -1
    for idx, line in enumerate(lines):
        if line.strip() == SECTION_HEADER:
            start = idx
            break
    if start == -1:
        raise RuntimeError("Architecture Appendices section not found in mkdocs.yml")
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if line.startswith("- "):
            break
        end += 1
    return start, end


def sync_nav(config_path: Path, appendix_paths: list[Path], *, dry_run: bool) -> bool:
    if not config_path.exists():
        raise RuntimeError(f"mkdocs.yml not found at {config_path}")

    lines = config_path.read_text(encoding="utf-8").splitlines()
    start, end = _find_section(lines)
    existing = _collect_existing(lines, start, end)

    managed_targets = {path.relative_to(paths.DOCS_ROOT).as_posix(): path for path in appendix_paths}
    managed_scope = set(managed_targets)
    managed_lines: list[str] = []
    remaining_targets = dict(managed_targets)

    # Preserve existing order for items already in the nav.
    for label, target in existing:
        if target in remaining_targets:
            managed_lines.append(f"{ITEM_INDENT}- {label}: {target}")
            remaining_targets.pop(target, None)

    # Append new files alphabetically.
    for rel in sorted(remaining_targets):
        path = remaining_targets[rel]
        label = _parse_label(path)
        managed_lines.append(f"{ITEM_INDENT}- {label}: {rel}")

    static_lines = [
        f"{ITEM_INDENT}- {label}: {target}"
        for label, target in existing
        if target not in managed_scope
    ]

    new_block = [SECTION_HEADER, *managed_lines, *static_lines]
    current_block = lines[start:end]
    if current_block == new_block:
        return False

    if dry_run:
        print("[nav.appendices] dry-run mode; nav would be updated:")
        for line in new_block[1:]:
            print(f"  {line.strip()}")
        return False

    updated = lines[:start] + new_block + lines[end:]
    config_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    print("[nav.appendices] updated navigation")
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ensure TDD appendices are listed in MkDocs nav.")
    parser.add_argument("--config", type=Path, default=MKDOCS_CONFIG, help="Path to mkdocs.yml")
    parser.add_argument("--appendix-dir", type=Path, default=APPENDICES_DIR, help="Directory containing appendix markdown files")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without editing files")
    return parser.parse_args(argv or sys.argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    appendix_files = discover_appendices(args.appendix_dir)
    try:
        sync_nav(args.config, appendix_files, dry_run=args.dry_run)
    except RuntimeError as exc:  # pragma: no cover
        print(f"[nav.appendices] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
