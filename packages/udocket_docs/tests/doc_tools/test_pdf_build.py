from __future__ import annotations

from pathlib import Path

import pytest

from doc_tools import pdf_build as pb
from doc_tools import paths


def _configure_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, patch_build: bool = True) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    site_dir = tmp_path / "doc-builds" / "sites" / "dev"
    pdf_dir = tmp_path / "doc-builds" / "pdf" / "dev"
    site_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(paths, "REPO_ROOT", tmp_path, raising=False)
    monkeypatch.setattr(pb, "DOCS_DIR", docs_dir, raising=False)
    monkeypatch.setattr(pb, "SITE_DIR", site_dir, raising=False)
    monkeypatch.setattr(pb, "BUILD_DIR", pdf_dir, raising=False)
    monkeypatch.setattr(pb, "MKDOCS_CONFIG", tmp_path / "mkdocs.yml", raising=False)
    (pb.MKDOCS_CONFIG).write_text("site_name: docs", encoding="utf-8")

    targets = (
        pb.PdfTarget(
            name="test",
            source=docs_dir / "overview" / "test.md",
            output=pdf_dir / "test.pdf",
            title="Test Document",
        ),
    )
    monkeypatch.setattr(pb, "PDF_TARGETS", targets, raising=False)
    target_source = targets[0].source
    target_source.parent.mkdir(parents=True, exist_ok=True)
    target_source.write_text("# Test", encoding="utf-8")
    html_path = targets[0].html_path()
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text("<html></html>", encoding="utf-8")

    class DummyHTML:
        def __init__(self, filename: str, base_url: str) -> None:
            self.filename = filename
            self.base_url = base_url

        def write_pdf(self, destination: str, stylesheets, presentational_hints: bool) -> None:  # type: ignore[no-untyped-def]
            Path(destination).write_text("pdf", encoding="utf-8")

    monkeypatch.setattr(pb, "HTML", DummyHTML, raising=False)
    if patch_build:
        monkeypatch.setattr(pb, "run_mkdocs_build", lambda: None, raising=False)


def test_pdf_build_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_environment(tmp_path, monkeypatch)

    rc = pb.main(["--skip-build"])

    assert rc == 0
    pdf_file = pb.BUILD_DIR / "test.pdf"
    assert pdf_file.exists()
    assert pdf_file.read_text(encoding="utf-8") == "pdf"


def test_pdf_build_missing_html(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_environment(tmp_path, monkeypatch)
    # Remove the generated HTML to trigger error
    targets = pb.PDF_TARGETS
    html_path = targets[0].html_path()
    html_path.unlink()

    with pytest.raises(FileNotFoundError):
        pb.main(["--skip-build"])


def test_pdf_build_runs_mkdocs_when_not_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_environment(tmp_path, monkeypatch, patch_build=False)
    invoked: list[None] = []

    def fake_build() -> None:
        invoked.append(None)

    monkeypatch.setattr(pb, "run_mkdocs_build", fake_build, raising=False)

    rc = pb.main([])

    assert rc == 0
    assert invoked == [None]


def test_pdf_build_missing_markdown_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_environment(tmp_path, monkeypatch)
    target = pb.PDF_TARGETS[0]
    target.source.unlink()

    with pytest.raises(FileNotFoundError):
        pb.main(["--skip-build"])


def test_pdf_build_target_filter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_environment(tmp_path, monkeypatch)
    pdf_dir = pb.BUILD_DIR
    extra_target = pb.PdfTarget(
        name="extra",
        source=pb.DOCS_DIR / "overview" / "extra.md",
        output=pdf_dir / "extra.pdf",
        title="Extra Doc",
    )
    extra_target.source.parent.mkdir(parents=True, exist_ok=True)
    extra_target.source.write_text("# Extra", encoding="utf-8")
    extra_html = extra_target.html_path()
    extra_html.parent.mkdir(parents=True, exist_ok=True)
    extra_html.write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(pb, "PDF_TARGETS", pb.PDF_TARGETS + (extra_target,), raising=False)

    rc = pb.main(["--skip-build", "--target", "extra"])

    assert rc == 0
    assert (extra_target.output).exists()
    assert not (pb.PDF_TARGETS[0].output).exists()
