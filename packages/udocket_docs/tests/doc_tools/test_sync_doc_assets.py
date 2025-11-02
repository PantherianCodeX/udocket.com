from __future__ import annotations

from pathlib import Path

import pytest

from doc_tools.sync import doc_assets as sync_assets


def test_doc_assets_dry_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "build" / "diagrams"
    source.mkdir(parents=True)
    (source / "diagram.svg").write_text("svg", encoding="utf-8")
    destination = tmp_path / "site" / "build" / "diagrams"

    rc = sync_assets.main(
        [
            "--dry-run",
            "--source",
            str(source),
            "--destination",
            str(destination),
        ]
    )

    assert rc == 0
    captured = capsys.readouterr()
    assert "would mirror" in captured.out
    assert not destination.exists()


def test_doc_assets_mirrors_tree(tmp_path: Path) -> None:
    source = tmp_path / "build" / "diagrams"
    source.mkdir(parents=True)
    (source / "diagram.svg").write_text("svg", encoding="utf-8")
    destination = tmp_path / "site" / "build" / "diagrams"

    rc = sync_assets.main(
        [
            "--source",
            str(source),
            "--destination",
            str(destination),
        ]
    )

    assert rc == 0
    mirrored = destination / "diagram.svg"
    assert mirrored.exists()
    assert mirrored.read_text(encoding="utf-8") == "svg"


def test_doc_assets_handles_missing_source(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "missing"
    destination = tmp_path / "site" / "build" / "diagrams"

    rc = sync_assets.main(
        [
            "--source",
            str(source),
            "--destination",
            str(destination),
        ]
    )

    assert rc == 0
    captured = capsys.readouterr()
    assert "source directory missing" in captured.out


def test_doc_assets_replaces_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "build" / "diagrams"
    source.mkdir(parents=True)
    (source / "diagram.svg").write_text("svg", encoding="utf-8")
    destination = tmp_path / "site" / "build" / "diagrams"
    destination.mkdir(parents=True)
    stale = destination / "old.svg"
    stale.write_text("old", encoding="utf-8")

    rc = sync_assets.main(
        [
            "--source",
            str(source),
            "--destination",
            str(destination),
        ]
    )

    assert rc == 0
    assert not stale.exists()
    assert (destination / "diagram.svg").exists()
