from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from doc_tools.build import pdf as pb


class DummyHTML:
    calls: List[tuple[str, list[object], bool]] = []

    def __init__(self, filename: str, base_url: str) -> None:
        self.filename = filename
        self.base_url = base_url

    def write_pdf(self, output: str, stylesheets: list[object], presentational_hints: bool) -> None:
        Path(output).write_text("pdf", encoding="utf-8")
        DummyHTML.calls.append((output, stylesheets, presentational_hints))


class DummyCSS:
    def __init__(self, filename: str) -> None:
        self.filename = filename


def _configure_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    docs = tmp_path / "docs"
    site = tmp_path / "site"
    build = tmp_path / "pdf"
    docs.mkdir()
    site.mkdir()
    build.mkdir()
    monkeypatch.setattr(pb.paths, "REPO_ROOT", tmp_path, raising=False)
    monkeypatch.setattr(pb, "DOCS_DIR", docs, raising=False)
    monkeypatch.setattr(pb, "SITE_DIR", site, raising=False)
    monkeypatch.setattr(pb, "BUILD_DIR", build, raising=False)
    monkeypatch.setattr(pb, "SHARED_CSS", docs / "assets" / "stylesheets" / "weasy.css", raising=False)
    css_path = pb.SHARED_CSS
    css_path.parent.mkdir(parents=True, exist_ok=True)
    css_path.write_text("body {}", encoding="utf-8")
    monkeypatch.setattr(pb, "CSS", DummyCSS, raising=False)
    monkeypatch.setattr(pb, "HTML", DummyHTML, raising=False)
    DummyHTML.calls.clear()
    return docs, site, build


def test_render_target_writes_pdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    docs, site, build = _configure_paths(tmp_path, monkeypatch)
    target = pb.PdfTarget(
        name="sample",
        source=docs / "sample.md",
        output=build / "sample.pdf",
        title="Sample",
    )
    target.source.parent.mkdir(parents=True, exist_ok=True)
    target.source.write_text("content", encoding="utf-8")
    target_html = site / "sample.html"
    target_html.parent.mkdir(parents=True, exist_ok=True)
    target_html.write_text("<html></html>", encoding="utf-8")

    pb.render_target(target)

    captured = capsys.readouterr()
    assert "sample.pdf" in captured.out
    assert target.output.read_text(encoding="utf-8") == "pdf"
    assert DummyHTML.calls and DummyHTML.calls[0][2] is True


def test_render_target_missing_html(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs, site, build = _configure_paths(tmp_path, monkeypatch)
    target = pb.PdfTarget(name="sample", source=docs / "sample.md", output=build / "sample.pdf", title="Sample")
    target.source.parent.mkdir(parents=True, exist_ok=True)
    target.source.write_text("content", encoding="utf-8")
    # do not create HTML file
    with pytest.raises(FileNotFoundError):
        pb.render_target(target)


def test_render_target_missing_markdown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, _, build = _configure_paths(tmp_path, monkeypatch)
    target = pb.PdfTarget(name="sample", source=tmp_path / "docs" / "missing.md", output=build / "sample.pdf", title="Sample")
    with pytest.raises(FileNotFoundError):
        pb.render_target(target)


def test_run_mkdocs_build_invokes_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    invoked: list[list[str]] = []

    def fake_run(cmd, check):  # type: ignore[no-untyped-def]
        invoked.append(cmd)
        return 0

    monkeypatch.setattr(pb.subprocess, "run", fake_run)
    pb.run_mkdocs_build()
    assert invoked
    assert "mkdocs" in invoked[0][0]


def test_main_filters_targets_and_skips_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs, site, build = _configure_paths(tmp_path, monkeypatch)
    target = pb.PdfTarget(name="sample", source=docs / "sample.md", output=build / "sample.pdf", title="Sample")
    target.source.parent.mkdir(parents=True, exist_ok=True)
    target.source.write_text("content", encoding="utf-8")
    target_html = site / "sample.html"
    target_html.parent.mkdir(parents=True, exist_ok=True)
    target_html.write_text("<html></html>", encoding="utf-8")

    monkeypatch.setattr(pb, "PDF_TARGETS", (target,), raising=False)

    invoked: list[str] = []
    monkeypatch.setattr(pb, "run_mkdocs_build", lambda: invoked.append("build"))

    rendered: list[str] = []
    original_render = pb.render_target

    def fake_render(target_obj: pb.PdfTarget) -> None:
        rendered.append(target_obj.name)
        original_render(target_obj)

    monkeypatch.setattr(pb, "render_target", fake_render, raising=False)

    rc = pb.main(["--target", "sample", "--skip-build"])

    assert rc == 0
    assert invoked == []
    assert rendered == ["sample"]


def test_main_runs_build_for_all_targets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs, site, build = _configure_paths(tmp_path, monkeypatch)
    target = pb.PdfTarget(name="sample", source=docs / "sample.md", output=build / "sample.pdf", title="Sample")
    target.source.parent.mkdir(parents=True, exist_ok=True)
    target.source.write_text("content", encoding="utf-8")
    target_html = site / "sample.html"
    target_html.parent.mkdir(parents=True, exist_ok=True)
    target_html.write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(pb, "PDF_TARGETS", (target,), raising=False)

    builds: list[str] = []
    monkeypatch.setattr(pb, "run_mkdocs_build", lambda: builds.append("ran"))

    monkeypatch.setattr(pb, "render_target", lambda target_obj: None, raising=False)

    rc = pb.main([])

    assert rc == 0
    assert builds == ["ran"]
