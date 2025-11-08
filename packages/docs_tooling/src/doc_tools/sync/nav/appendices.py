from __future__ import annotations

import argparse
import sys
from pathlib import Path
from doc_tools.config import paths
from doc_tools.common.doc_utils import read_doc_label
from doc_tools.common.nav_utils import collect_entries, find_section

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


def sync_nav(config_path: Path, appendix_paths: list[Path], *, dry_run: bool) -> bool:
    if not config_path.exists():
        raise RuntimeError(f"mkdocs.yml not found at {config_path}")

    lines = config_path.read_text(encoding="utf-8").splitlines()
    start, end = find_section(lines, SECTION_HEADER)
    existing = collect_entries(lines, start, end)

    managed_targets = {path.relative_to(paths.DOCS_ROOT).as_posix(): path for path in appendix_paths}
    managed_scope = set(managed_targets)
    managed_lines: list[str] = []
    remaining_targets = dict(managed_targets)

    # Preserve existing order for items already in the nav.
    for entry in existing:
        if entry.target in remaining_targets:
            managed_lines.append(f"{ITEM_INDENT}- {entry.label}: {entry.target}")
            remaining_targets.pop(entry.target, None)

    # Append new files alphabetically.
    for rel in sorted(remaining_targets):
        path = remaining_targets[rel]
        fallback_label = path.stem.replace("_", " ").title()
        label = read_doc_label(path, fallback=fallback_label)
        managed_lines.append(f"{ITEM_INDENT}- {label}: {rel}")

    static_lines = [
        f"{ITEM_INDENT}- {entry.label}: {entry.target}"
        for entry in existing
        if entry.target not in managed_scope
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
