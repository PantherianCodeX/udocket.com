from __future__ import annotations

from pathlib import Path

import pytest

from doc_tools.sync import doc_assets


def _setup_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    build_root = tmp_path / "render"
    build_root.mkdir()
    render_dir = build_root / "diagrams"
    dest_dir = docs_root / "build" / "diagrams"
    monkeypatch.setattr(doc_assets.paths, "DOCS_ROOT", docs_root)
    monkeypatch.setattr(doc_assets.paths, "BUILD_ROOT", build_root)
    monkeypatch.setattr(doc_assets.paths, "REPO_ROOT", tmp_path)
    return docs_root, render_dir, dest_dir, tmp_path


def _create_source(docs_root: Path) -> Path:
    diagram_dir = docs_root / "area" / "diagrams"
    diagram_dir.mkdir(parents=True, exist_ok=True)
    source = diagram_dir / "example.mmd"
    source.write_text("graph TD; A-->B;")
    return source


def _relative_svg(source: Path, docs_root: Path) -> Path:
    return doc_assets.render_mermaid.build_output_relative(source, docs_root).with_suffix(".svg")


def test_doc_assets_bootstrap(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    docs_root, render_dir, dest_dir, _ = _setup_environment(monkeypatch, tmp_path)
    source = _create_source(docs_root)
    rel_svg = _relative_svg(source, docs_root)

    def fake_collect(mode: str, *_args, **_kwargs) -> list[Path]:
        if mode in {"all", "changed"}:
            return [source]
        raise AssertionError(f"unexpected mode {mode}")

    calls: list[list[str]] = []

    def fake_main(argv: list[str]) -> int:
        calls.append(list(argv))
        out_dir = Path(argv[argv.index("--out-dir") + 1])
        out_path = out_dir / rel_svg
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("<svg/>", encoding="utf-8")
        return 0

    monkeypatch.setattr(doc_assets.render_mermaid, "collect_sources", fake_collect)
    monkeypatch.setattr(doc_assets.render_mermaid, "main", fake_main)

    result = doc_assets.main([])

    assert result == 0
    assert len(calls) == 1
    assert "--all" in calls[0]
    render_file = render_dir / rel_svg
    assert render_file.exists()
    assert render_file.stat().st_size > 0
    mirror_file = dest_dir / rel_svg
    assert mirror_file.exists()
    assert mirror_file.stat().st_size > 0


def test_doc_assets_changed_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    docs_root, render_dir, dest_dir, _ = _setup_environment(monkeypatch, tmp_path)
    source = _create_source(docs_root)
    rel_svg = _relative_svg(source, docs_root)
    cached = render_dir / rel_svg
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text("cached", encoding="utf-8")

    def fake_collect(mode: str, *_args, **_kwargs) -> list[Path]:
        if mode == "all":
            return [source]
        if mode == "changed":
            return [source]
        raise AssertionError(f"unexpected mode {mode}")

    runs: list[list[str]] = []

    def fake_main(argv: list[str]) -> int:
        runs.append(list(argv))
        return 0

    monkeypatch.setattr(doc_assets.render_mermaid, "collect_sources", fake_collect)
    monkeypatch.setattr(doc_assets.render_mermaid, "main", fake_main)

    result = doc_assets.main([])

    assert result == 0
    assert len(runs) == 1
    assert runs[0][0] == "--changed"
    mirror_file = dest_dir / rel_svg
    assert mirror_file.exists()
    assert mirror_file.stat().st_size > 0


def test_doc_assets_manifest_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    docs_root, render_dir, dest_dir, _ = _setup_environment(monkeypatch, tmp_path)
    source = _create_source(docs_root)
    rel_svg = _relative_svg(source, docs_root)

    def fake_collect(mode: str, *_args, **_kwargs) -> list[Path]:
        if mode in {"all", "changed"}:
            return [source]
        raise AssertionError(f"unexpected mode {mode}")

    def fake_main(argv: list[str]) -> int:
        out_dir = Path(argv[argv.index("--out-dir") + 1])
        out_path = out_dir / rel_svg
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("", encoding="utf-8")  # zero bytes
        return 0

    monkeypatch.setattr(doc_assets.render_mermaid, "collect_sources", fake_collect)
    monkeypatch.setattr(doc_assets.render_mermaid, "main", fake_main)

    result = doc_assets.main([])
    captured = capfd.readouterr()

    assert result == 1
    assert "Zero-byte render cache files" in captured.out
    assert str(render_dir / rel_svg) in captured.out
    assert not dest_dir.exists()


def test_doc_assets_mirror_validates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    docs_root, render_dir, dest_dir, _ = _setup_environment(monkeypatch, tmp_path)
    source = _create_source(docs_root)
    rel_svg = _relative_svg(source, docs_root)

    def fake_collect(mode: str, *_args, **_kwargs) -> list[Path]:
        if mode in {"all", "changed"}:
            return [source]
        raise AssertionError(f"unexpected mode {mode}")

    def fake_main(argv: list[str]) -> int:
        out_dir = Path(argv[argv.index("--out-dir") + 1])
        out_path = out_dir / rel_svg
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("<svg/>", encoding="utf-8")
        return 0

    original_copy_tree = doc_assets.copy_tree

    def fake_copy_tree(src: Path, dest: Path, *, dry_run: bool) -> bool:
        success = original_copy_tree(src, dest, dry_run=dry_run)
        if success and not dry_run:
            target = dest / rel_svg
            target.write_text("", encoding="utf-8")
        return success

    monkeypatch.setattr(doc_assets.render_mermaid, "collect_sources", fake_collect)
    monkeypatch.setattr(doc_assets.render_mermaid, "main", fake_main)
    monkeypatch.setattr(doc_assets, "copy_tree", fake_copy_tree)

    result = doc_assets.main([])
    captured = capfd.readouterr()

    assert result == 1
    assert "Zero-byte docs/build mirror files" in captured.out
    assert str(dest_dir / rel_svg) in captured.out
