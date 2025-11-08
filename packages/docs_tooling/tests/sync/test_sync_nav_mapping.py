from __future__ import annotations

from pathlib import Path

import pytest

from doc_tools.sync import nav_mapping as anm


def _setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    monkeypatch.setattr(anm, "DOCS_SRC", docs_root, raising=False)
    monkeypatch.setattr(anm, "PROJECT_ROOT", tmp_path, raising=False)
    return docs_root


def test_move_sources_renames_directories_and_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup(tmp_path, monkeypatch)

    mapping = {"legacy/service": "new/catalog/service"}
    monkeypatch.setattr(anm, "PATH_MAPPING", mapping, raising=False)

    legacy_dir = docs_root / "legacy" / "service"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "asset.txt").write_text("asset", encoding="utf-8")

    legacy_md = docs_root / "legacy" / "service.md"
    legacy_md.write_text("content", encoding="utf-8")

    anm.move_sources()

    new_dir = docs_root / "new" / "catalog" / "service"
    new_md = docs_root / "new" / "catalog" / "service.md"

    assert not legacy_dir.exists()
    assert not legacy_md.exists()
    assert new_dir.exists()
    assert (new_dir / "asset.txt").read_text(encoding="utf-8") == "asset"
    assert new_md.read_text(encoding="utf-8") == "content"


def test_move_sources_refuses_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup(tmp_path, monkeypatch)

    mapping = {"legacy": "already/existing"}
    monkeypatch.setattr(anm, "PATH_MAPPING", mapping, raising=False)

    (docs_root / "legacy").mkdir(parents=True)
    (docs_root / "legacy.md").write_text("content", encoding="utf-8")
    destination = docs_root / "already" / "existing"
    destination.mkdir(parents=True)

    with pytest.raises(RuntimeError):
        anm.move_sources()


def test_move_sources_refuses_file_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup(tmp_path, monkeypatch)

    mapping = {"old/service": "new/service"}
    monkeypatch.setattr(anm, "PATH_MAPPING", mapping, raising=False)

    (docs_root / "old" / "service.md").parent.mkdir(parents=True, exist_ok=True)
    (docs_root / "old" / "service.md").write_text("content", encoding="utf-8")
    destination = docs_root / "new" / "service.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("existing", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Refusing to overwrite existing file"):
        anm.move_sources()


def test_update_references_rewrites_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup(tmp_path, monkeypatch)
    mapping = {"old/path": "new/path"}
    monkeypatch.setattr(anm, "PATH_MAPPING", mapping, raising=False)

    # create candidate file and a binary-like file to ensure decode errors are ignored
    candidate = tmp_path / "project" / "file.txt"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("Refer to old/path for docs", encoding="utf-8")
    invalid = tmp_path / "project" / "broken.txt"
    invalid.write_bytes(b"\xff\x00\xfe")

    anm.update_references()

    assert candidate.read_text(encoding="utf-8") == "Refer to new/path for docs"
    assert invalid.read_bytes() == b"\xff\x00\xfe"


def test_main_invokes_move_and_update(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"move": 0, "update": 0, "move_dry": False, "update_dry": False}

    def fake_move(*, dry_run: bool = False) -> None:
        called["move"] += 1
        called["move_dry"] = dry_run

    def fake_update(*, dry_run: bool = False) -> None:
        called["update"] += 1
        called["update_dry"] = dry_run

    monkeypatch.setattr(anm, "move_sources", fake_move)
    monkeypatch.setattr(anm, "update_references", fake_update)

    rc = anm.main([])

    assert rc == 0
    assert called == {"move": 1, "update": 1, "move_dry": False, "update_dry": False}


def test_main_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    state = {"move": False, "update": False}

    def fake_move(*, dry_run: bool = False) -> None:
        state["move"] = dry_run

    def fake_update(*, dry_run: bool = False) -> None:
        state["update"] = dry_run

    monkeypatch.setattr(anm, "move_sources", fake_move)
    monkeypatch.setattr(anm, "update_references", fake_update)

    rc = anm.main(["--dry-run"])

    assert rc == 0
    assert state == {"move": True, "update": True}
