from __future__ import annotations

from pathlib import Path

import pytest

import doc_tools.render_mermaid as render_mermaid


def test_render_mermaid_cli_local(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cli_path = tmp_path / "node_modules" / ".bin" / "mmdc"
    cli_path.parent.mkdir(parents=True, exist_ok=True)
    cli_path.write_text("#!/bin/sh\n", encoding="utf-8")
    source_root = tmp_path / "docs"
    diagram_dir = source_root / "area" / "diagrams"
    diagram_dir.mkdir(parents=True, exist_ok=True)
    source = diagram_dir / "example.mmd"
    source.write_text("graph TD; A-->B;", encoding="utf-8")
    out_dir = tmp_path / "output"

    monkeypatch.setattr(render_mermaid, "CLI_PATH", cli_path)
    monkeypatch.setattr(render_mermaid.paths, "DOCS_ROOT", source_root)
    monkeypatch.setattr(render_mermaid.paths, "REPO_ROOT", tmp_path)

    commands: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool) -> None:
        commands.append(cmd)
        dest_index = cmd.index("-o") + 1
        dest_path = Path(cmd[dest_index])
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text("<svg/>", encoding="utf-8")

    monkeypatch.setattr(render_mermaid.subprocess, "run", fake_run)
    monkeypatch.setattr(render_mermaid, "postprocess_svg", lambda path: None)

    rc = render_mermaid.main(
        [
            "--all",
            "--src-root",
            str(source_root),
            "--out-dir",
            str(out_dir),
            "--diff-base",
            "origin/main",
        ]
    )

    assert rc == 0
    assert commands
    assert commands[0][0] == str(cli_path)
    rendered = out_dir / render_mermaid.build_output_relative(source, source_root).with_suffix(".svg")
    assert rendered.exists()


def test_render_mermaid_cli_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing_cli = tmp_path / "node_modules" / ".bin" / "mmdc"
    monkeypatch.setattr(render_mermaid, "CLI_PATH", missing_cli)

    with pytest.raises(SystemExit):
        render_mermaid.detect_cli()

    captured = capsys.readouterr()
    assert "Mermaid CLI not found" in captured.err
