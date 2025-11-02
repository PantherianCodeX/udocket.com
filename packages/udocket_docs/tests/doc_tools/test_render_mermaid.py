from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List

import pytest

from doc_tools import paths
from doc_tools import render_mermaid as rm


@pytest.fixture(autouse=True)
def reset_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    # reset cached service areas to default between tests
    paths.load_service_areas.cache_clear()
    yield
    paths.load_service_areas.cache_clear()


def _setup_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    repo_root = tmp_path
    docs_root = repo_root / "docs"
    diagrams_root = docs_root / "diagrams"
    build_root = repo_root / "build"
    diagrams_root.mkdir(parents=True)
    build_root.mkdir(parents=True)

    monkeypatch.setattr(paths, "REPO_ROOT", repo_root, raising=False)
    monkeypatch.setattr(paths, "DOCS_ROOT", docs_root, raising=False)
    monkeypatch.setattr(paths, "BUILD_ROOT", build_root, raising=False)

    monkeypatch.setattr(rm, "DEFAULT_SRC", diagrams_root, raising=False)
    monkeypatch.setattr(rm, "DEFAULT_OUT", build_root / "diagrams", raising=False)
    monkeypatch.setattr(rm, "DEFAULT_PUPPETEER_CONFIG", repo_root / "noop.json", raising=False)
    monkeypatch.setattr(rm, "DEFAULT_CONFIG", repo_root / "noop.mmd", raising=False)

    return diagrams_root, build_root / "diagrams"

def test_detect_cli_prefers_mmdc(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rm.shutil, "which", lambda _: "/usr/local/bin/mmdc")

    result = rm.detect_cli(None)

    assert result == ["/usr/local/bin/mmdc"]


def test_detect_cli_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rm.shutil, "which", lambda _: None)

    result = rm.detect_cli(None)

    assert result == ["npx", "--yes", "@mermaid-js/mermaid-cli"]


def test_git_changed_collects_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path
    output = "docs/diagram.mmd\n"
    process = subprocess.CompletedProcess(args=[], returncode=0, stdout=output, stderr="")
    monkeypatch.setattr(rm.subprocess, "run", lambda *_, **__: process)  # type: ignore[assignment]

    files = rm.git_changed("origin/main", repo_root)

    assert files == [repo_root / "docs/diagram.mmd"]


def test_git_changed_raises_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    process = subprocess.CompletedProcess(args=[], returncode=2, stdout="", stderr="fatal error")
    monkeypatch.setattr(rm.subprocess, "run", lambda *_, **__: process)  # type: ignore[assignment]

    with pytest.raises(RuntimeError):
        rm.git_changed("origin/main", Path("/repo"))


def test_render_mermaid_paths_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    diagrams_root, out_root = _setup_environment(tmp_path, monkeypatch)
    source = diagrams_root / "service" / "diagram.mmd"
    source.parent.mkdir(parents=True)
    source.write_text("graph LR; A-->B;", encoding="utf-8")

    calls: List[list[str]] = []

    def fake_run(cmd, check):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        out_index = cmd.index("-o") + 1
        dest = Path(cmd[out_index])
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("<svg/>", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(rm, "subprocess", subprocess)
    monkeypatch.setattr(rm.subprocess, "run", fake_run, raising=False)  # type: ignore[arg-type]

    processed: list[Path] = []
    monkeypatch.setattr(rm, "postprocess_svg", lambda p: processed.append(Path(p)))
    monkeypatch.setattr(rm, "detect_cli", lambda override=None: ["mock-cli"])

    rc = rm.main(["--paths", str(source)])

    assert rc == 0
    assert calls and calls[0][0] == "mock-cli"
    output_file = out_root / "service" / "diagram.svg"
    assert output_file.exists()
    assert processed == [output_file]


def test_render_mermaid_changed_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    diagrams_root, out_root = _setup_environment(tmp_path, monkeypatch)
    source = diagrams_root / "diagram.mmd"
    source.write_text("graph TD; A-->B;", encoding="utf-8")

    monkeypatch.setattr(rm, "DEFAULT_OUT", out_root, raising=False)
    monkeypatch.setattr(rm, "detect_cli", lambda override=None: ["mock-cli"])
    monkeypatch.setattr(rm, "git_changed", lambda diff_base, repo_root: [source])

    def fake_run(cmd, check):  # type: ignore[no-untyped-def]
        out_index = cmd.index("-o") + 1
        dest = Path(cmd[out_index])
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("<svg/>", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(rm, "subprocess", subprocess)
    monkeypatch.setattr(rm.subprocess, "run", fake_run, raising=False)  # type: ignore[arg-type]
    monkeypatch.setattr(rm, "postprocess_svg", lambda p: None)

    rc = rm.main(["--changed"])

    assert rc == 0
    assert (out_root / "diagram.svg").exists()


def test_render_file_applies_configs_and_verbose(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _setup_environment(tmp_path, monkeypatch)
    source = tmp_path / "docs" / "diagrams" / "diagram.mmd"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("graph TD;", encoding="utf-8")
    destination = tmp_path / "build" / "diagram.svg"
    puppeteer = tmp_path / "packages" / "udocket_docs" / "config" / "puppeteer.config.json"
    config = tmp_path / "packages" / "udocket_docs" / "config" / "mermaid.config.json"
    puppeteer.parent.mkdir(parents=True, exist_ok=True)
    puppeteer.write_text("{}", encoding="utf-8")
    config.write_text("{}", encoding="utf-8")

    invoked: list[list[str]] = []

    def fake_run(cmd, check):  # type: ignore[no-untyped-def]
        invoked.append(cmd)
        dest = Path(cmd[cmd.index("-o") + 1])
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("<svg/>", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(rm, "subprocess", subprocess)
    monkeypatch.setattr(rm.subprocess, "run", fake_run, raising=False)  # type: ignore[arg-type]
    marker: list[Path] = []
    monkeypatch.setattr(rm, "postprocess_svg", lambda p: marker.append(Path(p)))

    rm.render_file(
        source=source,
        destination=destination,
        cli=["mock-cli"],
        puppeteer_config=puppeteer,
        cli_config=config,
        fmt="svg",
        verbose=True,
    )

    captured = capsys.readouterr()
    assert "Rendering" in captured.out
    assert marker == [destination]
    assert any("-p" in cmd for cmd in invoked)
    assert any("-c" in cmd for cmd in invoked)


def test_render_mermaid_all_mode_cli_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    diagrams_root, out_root = _setup_environment(tmp_path, monkeypatch)
    first = diagrams_root / "first.mmd"
    second = diagrams_root / "nested" / "second.mmd"
    first.write_text("graph TD; A-->B;", encoding="utf-8")
    second.parent.mkdir(parents=True, exist_ok=True)
    second.write_text("graph TD; B-->C;", encoding="utf-8")

    calls: List[list[str]] = []

    def fake_run(cmd, check):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        out_index = cmd.index("-o") + 1
        dest = Path(cmd[out_index])
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("png", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(rm, "subprocess", subprocess)
    monkeypatch.setattr(rm.subprocess, "run", fake_run, raising=False)  # type: ignore[arg-type]
    monkeypatch.setattr(rm, "postprocess_svg", lambda p: None)

    rc = rm.main(
        [
            "--all",
            "--src-root",
            str(diagrams_root),
            "--out-dir",
            str(out_root),
            "--cli",
            "mmdc --no-sandbox",
            "--format",
            "png",
        ]
    )

    assert rc == 0
    assert len(calls) == 2
    assert calls[0][0] == "mmdc"
    assert (out_root / "first.png").exists()
    assert (out_root / "nested" / "second.png").exists()


def test_render_mermaid_handles_missing_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    diagrams_root, out_root = _setup_environment(tmp_path, monkeypatch)
    missing = diagrams_root / "missing.mmd"

    monkeypatch.setattr(rm, "detect_cli", lambda override=None: ["mock-cli"])
    called: list[list[str]] = []

    def fake_run(cmd, check):  # type: ignore[no-untyped-def]
        called.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(rm, "subprocess", subprocess)
    monkeypatch.setattr(rm.subprocess, "run", fake_run, raising=False)  # type: ignore[arg-type]

    rc = rm.main(["--paths", str(missing)])

    assert rc == 0
    assert called == []
    assert not (out_root / "missing.svg").exists()


def test_collect_sources_invalid_mode(tmp_path: Path) -> None:
    repo_root = tmp_path
    src_root = repo_root / "docs" / "diagrams"
    src_root.mkdir(parents=True)

    with pytest.raises(ValueError):
        rm.collect_sources("invalid", repo_root, src_root, "origin/main", [])


def test_main_no_sources_verbose(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rm, "collect_sources", lambda *args, **kwargs: [])
    monkeypatch.setattr(rm, "detect_cli", lambda override=None: ["mock-cli"])

    rc = rm.main(["--verbose"])

    assert rc == 0
