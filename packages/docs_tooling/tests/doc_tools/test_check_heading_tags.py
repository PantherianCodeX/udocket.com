from __future__ import annotations

from pathlib import Path

import pytest

from doc_tools import check_heading_tags as cht


def test_check_heading_tags_accepts_matching_anchor(tmp_path: Path) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text("## Example Heading {#example-heading}\n", encoding="utf-8")

    rc = cht.main([str(doc)])

    assert rc == 0


def test_check_heading_tags_flags_reserved_keywords(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text("## Example Heading (binding) {#example-heading-binding}\n", encoding="utf-8")

    rc = cht.main([str(doc)])

    captured = capsys.readouterr()
    assert rc == 1
    assert "reserved tag keyword" in captured.out


def test_check_heading_tags_detects_slug_mismatch(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text("## Example Heading {#wrong-slug}\n", encoding="utf-8")

    rc = cht.main([str(doc)])

    captured = capsys.readouterr()
    assert rc == 1
    assert "does not match slug" in captured.out


def test_check_heading_tags_handles_missing_anchor(tmp_path: Path) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text("## Example Heading\n", encoding="utf-8")

    issues = cht.check_file(doc)

    assert issues == []


def test_check_heading_tags_ignores_non_heading_lines(tmp_path: Path) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text("Not a heading line\n", encoding="utf-8")

    issues = cht.check_file(doc)

    assert issues == []


def test_check_heading_tags_warns_missing_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "missing.md"

    rc = cht.main([str(target)])

    captured = capsys.readouterr()
    assert rc == 1
    assert "does not exist" in captured.out


def test_check_heading_tags_skips_explicit_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    doc = tmp_path / "skip.md"
    doc.write_text("## Heading {#heading}\n", encoding="utf-8")
    cht.SKIP_FILES.add(doc)
    try:
        rc = cht.main([str(doc)])
    finally:
        cht.SKIP_FILES.discard(doc)

    assert rc == 0
