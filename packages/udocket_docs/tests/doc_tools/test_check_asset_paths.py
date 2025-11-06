from __future__ import annotations

from pathlib import Path

import pytest

from doc_tools import check_asset_paths


def _write_doc(base: Path, relative: str, content: str) -> Path:
    path = base / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture(name="docs_root")
def fixture_docs_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    monkeypatch.setattr(check_asset_paths.paths, "DOCS_ROOT", docs_root, raising=False)
    monkeypatch.setattr(check_asset_paths.paths, "REPO_ROOT", tmp_path, raising=False)
    return docs_root


def test_detects_reference_outside_docs(docs_root: Path) -> None:
    doc = _write_doc(
        docs_root,
        "automation/example.md",
        '<img src="../../build/diagrams/automation/example.svg">',
    )

    refs = check_asset_paths.collect_asset_references(doc)
    assert len(refs) == 1

    issues = check_asset_paths.check_paths([doc])
    assert issues
    assert "resolves outside docs/" in issues[0]


def test_allows_valid_relative_reference(docs_root: Path) -> None:
    doc = _write_doc(
        docs_root,
        "data/digital-signer.md",
        '<img src="../build/diagrams/data/digital-signer/example.svg">',
    )

    issues = check_asset_paths.check_paths([doc])

    assert not issues


def test_skip_absolute_and_external_links(docs_root: Path) -> None:
    doc = _write_doc(
        docs_root,
        "overview/index.md",
        """![Diagram](https://example.com/diagram.svg)
<img src="#fragment-only">
""",
    )

    issues = check_asset_paths.check_paths([doc])
    assert not issues


def test_main_returns_failure(monkeypatch: pytest.MonkeyPatch, docs_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_doc(
        docs_root,
        "automation/example.md",
        '<img src="../../build/diagrams/automation/example.svg">',
    )

    monkeypatch.chdir(docs_root.parent)
    rc = check_asset_paths.main(["docs"])

    captured = capsys.readouterr()
    assert rc == 1
    assert "Embedded asset path issues" in captured.out


def test_main_success(monkeypatch: pytest.MonkeyPatch, docs_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_doc(
        docs_root,
        "automation/example.md",
        '<img src="../build/diagrams/automation/example.svg">',
    )

    monkeypatch.chdir(docs_root.parent)
    rc = check_asset_paths.main(["docs"])

    captured = capsys.readouterr()
    assert rc == 0
    assert "validated successfully" in captured.out
