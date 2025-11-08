from __future__ import annotations

from pathlib import Path

import pytest
from doc_tools.sync.nav import appendices


def _mkdocs_template() -> str:
    return "\n".join(
        [
            "site_name: Test",
            "nav:",
            "- Home: index.md",
            "- Architecture Appendices:",
            "    - Glossary: overview/tdd/appendices/glossary.md",
            "    - Core Packaging Strategy: architecture/udocket-core-packaging.md",
            "- Decision Records:",
        ]
    )


def test_appendices_nav_adds_entries(tmp_path: Path) -> None:
    config = tmp_path / "mkdocs.yml"
    config.write_text(_mkdocs_template(), encoding="utf-8")

    appendix_dir = tmp_path / "docs" / "overview" / "tdd" / "appendices"
    appendix_dir.mkdir(parents=True)
    repo_trees = appendix_dir / "repository_trees.md"
    repo_trees.write_text(
        "---\ntitle: Repo Trees\n---\n\nContent\n",
        encoding="utf-8",
    )

    original_docs_root = appendices.paths.DOCS_ROOT
    try:
        appendices.paths.DOCS_ROOT = tmp_path / "docs"
        appendices.sync_nav(config, [repo_trees], dry_run=False)
    finally:
        appendices.paths.DOCS_ROOT = original_docs_root

    updated = config.read_text(encoding="utf-8")
    assert "repository_trees.md" in updated
    assert "Core Packaging Strategy" in updated


def test_appendices_nav_dry_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = tmp_path / "mkdocs.yml"
    config.write_text(_mkdocs_template(), encoding="utf-8")
    appendix_dir = tmp_path / "appendices"
    appendix_dir.mkdir()
    file_path = appendix_dir / "glossary.md"
    file_path.write_text("---\ntitle: Glossary\n---\n", encoding="utf-8")

    original_docs_root = appendices.paths.DOCS_ROOT
    try:
        appendices.paths.DOCS_ROOT = tmp_path
        appendices.sync_nav(config, [file_path], dry_run=True)
    finally:
        appendices.paths.DOCS_ROOT = original_docs_root

    captured = capsys.readouterr()
    assert "dry-run mode" in captured.out


def test_appendices_nav_is_idempotent(tmp_path: Path) -> None:
    config = tmp_path / "mkdocs.yml"
    config.write_text(_mkdocs_template(), encoding="utf-8")

    docs_root = tmp_path / "docs"
    appendix_path = docs_root / "overview" / "tdd" / "appendices" / "glossary.md"
    appendix_path.parent.mkdir(parents=True, exist_ok=True)
    appendix_path.write_text("---\ntitle: Glossary\n---\n", encoding="utf-8")

    original_docs_root = appendices.paths.DOCS_ROOT
    try:
        appendices.paths.DOCS_ROOT = docs_root
        before = config.read_text(encoding="utf-8")
        appendices.sync_nav(config, [appendix_path], dry_run=False)
    finally:
        appendices.paths.DOCS_ROOT = original_docs_root

    after = config.read_text(encoding="utf-8")
    assert after == before
