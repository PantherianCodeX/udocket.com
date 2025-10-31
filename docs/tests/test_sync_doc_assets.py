from __future__ import annotations

from pathlib import Path

import pytest

from docs.tools.sync import doc_assets as sync_assets


def test_doc_assets_dry_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    build_dir = tmp_path / "docs" / "build" / "mermaid"
    build_dir.mkdir(parents=True)
    (build_dir / "diagram.svg").write_text("svg", encoding="utf-8")

    monkeypatch.setattr(sync_assets, "ROOT", tmp_path)
    monkeypatch.setattr(sync_assets, "SRC_ROOT", tmp_path / "docs" / "src")
    monkeypatch.setattr(sync_assets, "ASSET_ROOT", tmp_path / "docs" / "src" / "_assets")
    monkeypatch.setattr(sync_assets, "MERMAID_SOURCE", build_dir)
    monkeypatch.setattr(sync_assets, "MERMAID_TARGET", tmp_path / "docs" / "src" / "_assets" / "mermaid")

    rc = sync_assets.main(["--dry-run"])

    captured = capsys.readouterr()
    assert rc == 0
    assert "would mirror" in captured.out
    assert not (sync_assets.MERMAID_TARGET).exists()


def test_doc_assets_mirrors_tree(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    build_dir = tmp_path / "docs" / "build" / "mermaid"
    build_dir.mkdir(parents=True)
    (build_dir / "diagram.svg").write_text("svg", encoding="utf-8")

    target_root = tmp_path / "docs" / "src" / "_assets"

    monkeypatch.setattr(sync_assets, "ROOT", tmp_path)
    monkeypatch.setattr(sync_assets, "SRC_ROOT", tmp_path / "docs" / "src")
    monkeypatch.setattr(sync_assets, "ASSET_ROOT", target_root)
    monkeypatch.setattr(sync_assets, "MERMAID_SOURCE", build_dir)
    monkeypatch.setattr(sync_assets, "MERMAID_TARGET", target_root / "mermaid")

    rc = sync_assets.main([])

    assert rc == 0
    mirrored = target_root / "mermaid" / "diagram.svg"
    assert mirrored.exists()
    assert mirrored.read_text(encoding="utf-8") == "svg"


def test_doc_assets_handles_missing_source(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sync_assets, "ROOT", tmp_path)
    monkeypatch.setattr(sync_assets, "SRC_ROOT", tmp_path / "docs" / "src")
    monkeypatch.setattr(sync_assets, "ASSET_ROOT", tmp_path / "docs" / "src" / "_assets")
    missing_source = tmp_path / "docs" / "build" / "mermaid"
    monkeypatch.setattr(sync_assets, "MERMAID_SOURCE", missing_source)
    monkeypatch.setattr(sync_assets, "MERMAID_TARGET", tmp_path / "docs" / "src" / "_assets" / "mermaid")

    rc = sync_assets.main([])

    captured = capsys.readouterr()
    assert rc == 0
    assert "source directory missing" in captured.out
