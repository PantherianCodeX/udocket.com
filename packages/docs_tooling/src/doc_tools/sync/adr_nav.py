from __future__ import annotations

import argparse
import sys
from pathlib import Path
from doc_tools.config import paths
from doc_tools.common.doc_utils import read_doc_label
from doc_tools.common.nav_utils import collect_entries, find_section

MKDOCS_CONFIG = paths.DOCS_PACKAGE_ROOT / "mkdocs.yml"
ADR_DIR = paths.DOCS_ROOT / "adr"
ADR_SECTION_TITLE = "- Decision Records:"
INDEX_LABEL = "Index"
INDEX_INDENT = "  "
ITEM_INDENT = "    "


def discover_adrs(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.glob("*.md")
        if path.is_file() and not path.name.startswith("_")
    )


def _build_entries(adrs: list[Path], existing: dict[str, str]) -> list[str]:
    overview: Path | None = None
    others: list[Path] = []
    for adr in adrs:
        if adr.name.lower() == "readme.md":
            overview = adr
        else:
            others.append(adr)
    lines: list[str] = [f"{INDEX_INDENT}- {INDEX_LABEL}:"]
    if overview:
        rel = overview.relative_to(paths.DOCS_ROOT).as_posix()
        label = existing.get(rel) or read_doc_label(overview, heading_prefixes=("ADR",))
        lines.append(f"{ITEM_INDENT}- {label}: {rel}")
    for adr in others:
        rel = adr.relative_to(paths.DOCS_ROOT).as_posix()
        label = existing.get(rel) or read_doc_label(adr, heading_prefixes=("ADR",))
        lines.append(f"{ITEM_INDENT}- {label}: {rel}")
    return lines


def sync_nav(config_path: Path, adr_paths: list[Path], *, dry_run: bool) -> bool:
    if not config_path.exists():
        raise RuntimeError(f"mkdocs.yml not found at {config_path}")
    lines = config_path.read_text(encoding="utf-8").splitlines()
    start, end = find_section(lines, ADR_SECTION_TITLE)
    existing_pairs = collect_entries(lines, start, end)
    existing = {entry.target: entry.label for entry in existing_pairs}
    new_entries = _build_entries(adr_paths, existing)
    current_entries = lines[start + 1 : end]
    if current_entries == new_entries:
        return False
    if dry_run:
        print("[adr-nav] dry-run mode; nav would be updated:")
        for line in new_entries:
            print(f"  {line.strip()}")
        return False
    updated = lines[: start + 1] + new_entries + lines[end:]
    config_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    print("nav updated")
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ensure ADR entries are present in MkDocs navigation.")
    parser.add_argument("--config", type=Path, default=MKDOCS_CONFIG, help="Path to mkdocs.yml")
    parser.add_argument("--adr-dir", type=Path, default=ADR_DIR, help="Directory containing ADR markdown files")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without editing files")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    adr_files = discover_adrs(args.adr_dir)
    try:
        sync_nav(args.config, adr_files, dry_run=args.dry_run)
    except RuntimeError as exc:
        print(f"[adr-nav] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
