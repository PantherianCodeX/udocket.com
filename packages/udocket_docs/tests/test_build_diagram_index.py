from __future__ import annotations

from pathlib import Path

import pytest

from doc_tools.build import diagram_index as bdi


def _setup_diagram_env(tmp_path: Path) -> None:
    src_dir = tmp_path / "docs"
    appendix = src_dir / "overview" / "tdd" / "appendices" / "diagrams.md"
    appendix.parent.mkdir(parents=True, exist_ok=True)
    appendix.write_text(
        "\n".join(
            [
                "---",
                "title: diagrams",
                "---",
                "",
                "## Overview",
                "",
                bdi.BEGIN_MARKER,
                "_placeholder_",
                bdi.END_MARKER,
            ]
        ),
        encoding="utf-8",
    )

    service_dir = src_dir / "services" / "alpha"
    diagram_dir = service_dir / "diagrams"
    diagram_dir.mkdir(parents=True, exist_ok=True)
    (service_dir.with_suffix(".md")).write_text("# Alpha\n", encoding="utf-8")

    (diagram_dir / "alpha-flow-v1.mmd").write_text(
        "%% id: alpha-flow\n%% version: v1\nflowchart LR; A-->B;\n", encoding="utf-8"
    )
    (diagram_dir / "alpha-other-v2.mmd").write_text("flowchart LR; B-->C;\n", encoding="utf-8")
    beta_dir = src_dir / "services" / "beta" / "diagrams"
    beta_dir.mkdir(parents=True, exist_ok=True)
    (beta_dir / "beta-graph.mmd").write_text(
        "%% note without colon\n%% version: v3\n\nflowchart LR; C-->D;\n",
        encoding="utf-8",
    )

    root_diagram = src_dir / "diagrams"
    root_diagram.mkdir(parents=True, exist_ok=True)
    (root_diagram / "root-only.mmd").write_text(
        "%% id: root-only\n%%  \n%% comment-without-colon\nflowchart LR; E-->F;\n",
        encoding="utf-8",
    )
    build_dir = src_dir / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "ignored.mmd").write_text("flowchart LR; G-->H;\n", encoding="utf-8")


def test_build_content_renders_tables(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_diagram_env(tmp_path)
    src_dir = tmp_path / "docs"
    appendix = src_dir / "overview" / "tdd" / "appendices" / "diagrams.md"

    monkeypatch.setattr(bdi, "DOCS_DIR", src_dir)
    monkeypatch.setattr(bdi, "APPENDIX_FILE", appendix)
    monkeypatch.setattr(bdi, "APPENDIX_DIR", appendix.parent)

    result = bdi.build_content()

    assert "alpha-flow" in result
    assert "| `alpha-flow` | v1 |" in result
    assert "| `alpha-other-v2` | v2 |" in result
    assert "| `root-only` | — |" in result
    assert 'class="glightbox"' in result


def test_main_updates_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_diagram_env(tmp_path)
    src_dir = tmp_path / "docs"
    appendix = src_dir / "overview" / "tdd" / "appendices" / "diagrams.md"

    monkeypatch.setattr(bdi, "DOCS_DIR", src_dir)
    monkeypatch.setattr(bdi, "APPENDIX_FILE", appendix)
    monkeypatch.setattr(bdi, "APPENDIX_DIR", appendix.parent)

    rc = bdi.main([])
    assert rc == 0

    refreshed = appendix.read_text(encoding="utf-8")
    assert "alpha-flow" in refreshed

    rc_check = bdi.main(["--check"])
    assert rc_check == 0


def test_collect_diagrams_covers_orphans(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_diagram_env(tmp_path)
    src_dir = tmp_path / "docs"
    monkeypatch.setattr(bdi, "DOCS_DIR", src_dir)

    diagrams = bdi.collect_diagrams()

    assert any(key is None for key in diagrams.keys())
    assert len(diagrams) >= 2


def test_render_groups_handles_empty() -> None:
    rendered = bdi.render_groups([])
    assert "_No diagrams detected._" in rendered


def test_main_flags_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _setup_diagram_env(tmp_path)
    src_dir = tmp_path / "docs"
    appendix = src_dir / "overview" / "tdd" / "appendices" / "diagrams.md"

    monkeypatch.setattr(bdi, "DOCS_DIR", src_dir)
    monkeypatch.setattr(bdi, "APPENDIX_FILE", appendix)
    monkeypatch.setattr(bdi, "APPENDIX_DIR", appendix.parent)

    # Leave file stale so check should fail
    rc = bdi.main(["--check"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "stale" in captured.err
