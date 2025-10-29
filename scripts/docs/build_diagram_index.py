#!/usr/bin/env python3
"""Generate the TDD diagrams index appendix."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Sequence
import re

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent

ROOT_PATH = str(ROOT_DIR)


def _ensure_root_on_path() -> None:
    if ROOT_PATH not in sys.path:
        sys.path.insert(0, ROOT_PATH)


_ensure_root_on_path()

from scripts.docs import doc_utils  # type: ignore  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "docs" / "src"
APPENDIX_FILE = SRC_DIR / "overview" / "tdd" / "appendices" / "diagrams.md"
APPENDIX_DIR = APPENDIX_FILE.parent
BEGIN_MARKER = "<!-- BEGIN AUTO-GENERATED DIAGRAM INDEX -->"
END_MARKER = "<!-- END AUTO-GENERATED DIAGRAM INDEX -->"


@dataclass
class Diagram:
    slug: str
    version: str
    source_rel: Path
    svg_rel: Path
    metadata: Dict[str, str]


@dataclass
class OwnerGroup:
    doc_path: Path | None
    display_name: str
    entries: list[Diagram]


def parse_metadata(path: Path) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not line.startswith("%%"):
            break
        line = line[2:].strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip().lower()] = value.strip()
    return metadata


def determine_owner(path: Path) -> Path | None:
    rel = path.relative_to(SRC_DIR)
    parts = list(rel.parts)
    if "diagrams" not in parts:
        return None
    idx = parts.index("diagrams")
    if idx == 0:
        return None
    owner_parts = parts[:idx]
    owner_path = SRC_DIR.joinpath(*owner_parts).with_suffix(".md")
    if owner_path.exists():
        return owner_path
    return None


def derive_version(metadata: Dict[str, str], stem: str) -> str:
    version = metadata.get("version", "")
    if version:
        return version
    match = re.search(r"(?:^|[-_])v(\d+)$", stem.lower())
    if match:
        return f"v{match.group(1)}"
    return ""


def collect_diagrams() -> Dict[Path | None, list[Diagram]]:
    diagrams: Dict[Path | None, list[Diagram]] = {}
    for path in sorted(SRC_DIR.rglob("*.mmd")):
        rel = path.relative_to(SRC_DIR)
        if "build" in rel.parts:
            continue
        if "diagrams" not in rel.parts:
            continue

        metadata = parse_metadata(path)
        slug = metadata.get("id") or path.stem
        version = derive_version(metadata, path.stem)
        owner_doc = determine_owner(path)
        source_rel = rel
        svg_rel = Path("build/mermaid").joinpath(rel).with_suffix(".svg")

        group = diagrams.setdefault(owner_doc, [])
        group.append(
            Diagram(
                slug=slug,
                version=version,
                source_rel=source_rel,
                svg_rel=svg_rel,
                metadata=metadata,
            )
        )
    return diagrams


def owner_display(owner_doc: Path | None) -> str:
    if owner_doc is None:
        return "Unattributed"
    lines = doc_utils.read_markdown_lines(owner_doc)
    front = doc_utils.parse_front_matter(lines)
    title = doc_utils.stringify(front.get("title", ""))
    fallback = owner_doc.relative_to(SRC_DIR).as_posix()
    return doc_utils.derive_doc_label(title, fallback=fallback)


def build_groups(diagrams: Dict[Path | None, list[Diagram]]) -> list[OwnerGroup]:
    groups: list[OwnerGroup] = []
    for owner_doc, entries in diagrams.items():
        label = owner_display(owner_doc)
        entries_sorted = sorted(entries, key=lambda d: (d.slug.lower(), d.version))
        groups.append(
            OwnerGroup(
                doc_path=owner_doc,
                display_name=label,
                entries=entries_sorted,
            )
        )
    groups.sort(key=lambda g: g.display_name.lower())
    return groups


def rel_from_appendix(target: Path) -> str:
    return Path(os.path.relpath(target, APPENDIX_DIR)).as_posix()


def render_table_row(diagram: Diagram) -> str:
    version = diagram.version or "—"
    source_link = rel_from_appendix(SRC_DIR / diagram.source_rel)
    svg_link = rel_from_appendix(SRC_DIR / diagram.svg_rel)
    thumb_html = (
        f'<a class="glightbox" href="{svg_link}" data-type="image">'
        f'<img src="{svg_link}" alt="{diagram.slug} diagram" '
        'style="max-height: 160px; max-width: 200px; width: auto; height: auto; '
        'border: 1px solid #d0d0d0; border-radius: 4px; vertical-align: middle;"></a>'
    )
    return (
        f"| `{diagram.slug}` | {version} | "
        f"[`{diagram.source_rel.as_posix()}`]({source_link}) | "
        f"[`{diagram.svg_rel.as_posix()}`]({svg_link}) | "
        f"{thumb_html} |"
    )


def render_groups(groups: Sequence[OwnerGroup]) -> str:
    lines: list[str] = []
    lines.append("<!-- AUTO-GENERATED: Run `python scripts/docs/build_diagram_index.py` to refresh. -->")
    lines.append("")
    if not groups:
        lines.append("_No diagrams detected._")
        lines.append("")
        return "\n".join(lines)

    for group in groups:
        if group.doc_path:
            doc_rel = rel_from_appendix(group.doc_path)
            lines.append(f"### [{group.display_name}]({doc_rel})")
        else:
            lines.append(f"### {group.display_name}")
        lines.append("")
        lines.append("| Diagram | Version | Mermaid source | Rendered SVG | Preview |")
        lines.append("| ------- | ------- | -------------- | ------------ | ------- |")
        for entry in group.entries:
            lines.append(render_table_row(entry))
        lines.append("")
    return "\n".join(lines)


def build_content() -> str:
    diagrams = collect_diagrams()
    groups = build_groups(diagrams)
    appendix_text = APPENDIX_FILE.read_text(encoding="utf-8")
    generated = render_groups(groups)
    return doc_utils.replace_marked_section(appendix_text, BEGIN_MARKER, END_MARKER, generated)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify index is up to date")
    args = parser.parse_args(argv)

    updated_content = build_content()

    if args.check:
        current = APPENDIX_FILE.read_text(encoding="utf-8")
        if current != updated_content:
            print("Diagrams index is stale. Run build_diagram_index.py to refresh.", file=sys.stderr)
            return 1
        return 0

    APPENDIX_FILE.write_text(updated_content, encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
