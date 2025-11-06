from __future__ import annotations

from pathlib import Path

import pytest

from doc_tools.sync import adr_nav


def _mkdocs_template(entries: list[str]) -> str:
    lines = ["nav:", "- Decision Records:"]
    lines.extend(entries)
    return "\n".join(lines) + "\n"


def test_adr_nav_updates_when_new_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    docs_root = tmp_path / "docs"
    adr_dir = docs_root / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)
    overview = adr_dir / "README.md"
    overview.write_text("# Overview\n", encoding="utf-8")
    new_adr = adr_dir / "ADR-0006-example.md"
    new_adr.write_text("# ADR-0006 — Example Decision\n", encoding="utf-8")
    config_path = tmp_path / "mkdocs.yml"
    config_path.write_text(_mkdocs_template(["  - Index:", "    - Overview: adr/README.md"]), encoding="utf-8")

    adr_paths = [overview, new_adr]
    adr_paths.sort()
    original_docs_root = adr_nav.paths.DOCS_ROOT
    try:
        adr_nav.paths.DOCS_ROOT = docs_root
        updated = adr_nav.sync_nav(config_path, adr_paths, dry_run=False)
    finally:
        adr_nav.paths.DOCS_ROOT = original_docs_root

    assert updated is True
    captured = capsys.readouterr()
    assert "nav updated" in captured.out
    updated_lines = config_path.read_text(encoding="utf-8").splitlines()
    assert "  - Index:" in updated_lines
    assert "    - Overview: adr/README.md" in updated_lines
    assert "    - Example Decision: adr/ADR-0006-example.md" in updated_lines


def test_adr_nav_skips_template_and_orders_entries(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs"
    adr_dir = docs_root / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)
    overview = adr_dir / "README.md"
    overview.write_text("# Overview\n", encoding="utf-8")
    template = adr_dir / "_template.md"
    template.write_text("# Template\n", encoding="utf-8")
    adr_file = adr_dir / "ADR-0007-sample.md"
    adr_file.write_text("# ADR-0007 — Sample Decision\n", encoding="utf-8")
    config_path = tmp_path / "mkdocs.yml"
    config_path.write_text(_mkdocs_template([]), encoding="utf-8")

    original_docs_root = adr_nav.paths.DOCS_ROOT
    try:
        adr_nav.paths.DOCS_ROOT = docs_root
        adr_paths = adr_nav.discover_adrs(adr_dir)
        assert template not in adr_paths
        sync_lines = adr_nav._build_entries(adr_paths, {})
    finally:
        adr_nav.paths.DOCS_ROOT = original_docs_root

    assert sync_lines[0] == "  - Index:"
    assert sync_lines[1].endswith("adr/README.md")
    assert sync_lines[2].endswith("adr/ADR-0007-sample.md")
