from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

from doc_tools import paths

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


def _derive_label(path: Path) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return path.stem
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if "—" in heading:
                _, remainder = heading.split("—", 1)
                return remainder.strip() or path.stem
            if "-" in heading:
                prefix, remainder = heading.split("-", 1)
                if prefix.strip().upper().startswith("ADR"):
                    return remainder.strip() or path.stem
            return heading or path.stem
    return path.stem


def _parse_entry(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped.startswith("- "):
        return None
    body = stripped[2:]
    if ":" not in body:
        return None
    label, target = body.split(":", 1)
    return label.strip(), target.strip()


def _collect_existing(lines: Iterable[str], start: int, end: int) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for idx in range(start, end):
        if ":" not in lines[idx]:
            continue
        parsed = _parse_entry(lines[idx])
        if not parsed:
            continue
        label, target = parsed
        mapping[target] = label
    return mapping


def _find_section(lines: list[str]) -> tuple[int, int]:
    start = -1
    for idx, line in enumerate(lines):
        if line.strip() == ADR_SECTION_TITLE:
            start = idx
            break
    if start == -1:
        raise RuntimeError("Decision Records section not found in mkdocs.yml")
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if line.startswith("- "):
            break
        end += 1
    return start, end


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
        label = existing.get(rel) or _derive_label(overview)
        lines.append(f"{ITEM_INDENT}- {label}: {rel}")
    for adr in others:
        rel = adr.relative_to(paths.DOCS_ROOT).as_posix()
        label = existing.get(rel) or _derive_label(adr)
        lines.append(f"{ITEM_INDENT}- {label}: {rel}")
    return lines


def sync_nav(config_path: Path, adr_paths: list[Path], *, dry_run: bool) -> bool:
    if not config_path.exists():
        raise RuntimeError(f"mkdocs.yml not found at {config_path}")
    lines = config_path.read_text(encoding="utf-8").splitlines()
    start, end = _find_section(lines)
    existing = _collect_existing(lines, start + 1, end)
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
