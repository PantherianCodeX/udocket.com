from __future__ import annotations

from pathlib import Path

import pytest

from doc_tools import check_links as lc


def test_check_diagrams_detects_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(lc, "ROOT", tmp_path)
    content = "![Diagram](docs/platform/sample/diagrams/flow.mmd)"

    problems = lc.check_diagrams(content)

    assert problems == ["Missing diagram source: docs/platform/sample/diagrams/flow.mmd"]


def test_check_diagrams_pass(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    diagram = tmp_path / "docs" / "platform" / "sample" / "diagrams" / "flow.mmd"
    diagram.parent.mkdir(parents=True)
    diagram.write_text("graph TD;", encoding="utf-8")
    monkeypatch.setattr(lc, "ROOT", tmp_path)
    content = "![Diagram](docs/platform/sample/diagrams/flow.mmd)"

    problems = lc.check_diagrams(content)

    assert problems == []


def test_check_appendices_all_defined() -> None:
    text = "See App.A and App.B.\n\n## Appendix A\n## Appendix B"

    assert lc.check_appendices(text) == []


def test_check_appendices_missing_definition() -> None:
    text = "See App.B and App.Z.\n\n## Appendix B"

    problems = lc.check_appendices(text)

    assert problems == ["Appendix referenced but not defined in TDD: App.Z"]


def test_check_sections_missing_reference() -> None:
    text = "Refer to §2.\n\n## 1) Intro\n## 3) Later"

    assert lc.check_sections(text) == ["Section referenced but missing major heading: §2)"]


def test_main_strict_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doc = tmp_path / "docs" / "overview"
    doc.mkdir(parents=True)
    path = doc / "tdd.md"
    path.write_text("See App.Z.", encoding="utf-8")
    monkeypatch.setattr(lc, "ROOT", tmp_path)
    monkeypatch.setattr(lc, "DOC", path)
    monkeypatch.setenv("STRICT_DOCS", "1")

    rc = lc.main()

    captured = capsys.readouterr()
    assert rc == 1
    assert "Appendix referenced but not defined" in captured.out


def test_main_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doc = tmp_path / "docs" / "overview"
    doc.mkdir(parents=True)
    path = doc / "tdd.md"
    path.write_text("## 1) Intro\nSee App.A.\n## Appendix A\n", encoding="utf-8")
    monkeypatch.setattr(lc, "ROOT", tmp_path)
    monkeypatch.setattr(lc, "DOC", path)
    monkeypatch.delenv("STRICT_DOCS", raising=False)

    rc = lc.main()

    captured = capsys.readouterr()
    assert rc == 0
    assert "Docs check passed" in captured.out


def test_find_service_refs_handles_anchor() -> None:
    refs = lc.find_service_refs("See ../platform/foo.md#section-1 and ../automation/bar.md")

    assert refs == {("platform", "foo.md#section-1"), ("automation", "bar.md")}


def test_check_services_missing_anchor(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    services_dir = tmp_path / "docs" / "platform"
    services_dir.mkdir(parents=True)
    service = services_dir / "foo.md"
    service.write_text("## Heading Without Anchor\n", encoding="utf-8")
    monkeypatch.setitem(lc.AREA_PATHS, "platform", services_dir)
    lc.load_service_anchors.cache_clear()

    problems = lc.check_services("See ../platform/foo.md#missing-anchor")

    assert problems == ["Anchor '#missing-anchor' missing in ../platform/foo.md"]


def test_check_services_pass(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    services_dir = tmp_path / "docs" / "automation"
    services_dir.mkdir(parents=True)
    service = services_dir / "bar.md"
    service.write_text("## Heading {#section-1}\n", encoding="utf-8")
    monkeypatch.setitem(lc.AREA_PATHS, "automation", services_dir)
    lc.load_service_anchors.cache_clear()

    problems = lc.check_services("See ../automation/bar.md#section-1")

    assert problems == []
