from __future__ import annotations

from pathlib import Path

import pytest

from doc_tools.check import document_controls_tags as checker


def _write_doc(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def test_check_file_accepts_marked_section(tmp_path: Path) -> None:
    doc = tmp_path / "doc.md"
    content = """## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Docs Team |
<!-- END AUTO-GENERATED: document-controls -->
"""
    _write_doc(doc, content)

    issues = checker.check_file(doc)

    assert issues == []


def test_check_file_flags_missing_markers(tmp_path: Path) -> None:
    doc = tmp_path / "doc.md"
    content = """## Document Controls

| Field | Value |
| --- | --- |
| Authors | Docs Team |
"""
    _write_doc(doc, content)

    issues = checker.check_file(doc)

    assert len(issues) == 2
    assert "missing '<!-- BEGIN AUTO-GENERATED: document-controls -->' marker" in issues[0].detail


def test_main_reports_missing_markers(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doc = tmp_path / "doc.md"
    _write_doc(
        doc,
        """## Document Controls

| Field | Value |
| --- | --- |
| Authors | Docs Team |
""",
    )

    rc = checker.main([str(doc)])

    captured = capsys.readouterr()
    assert rc == 1
    assert "Document Controls marker issues detected" in captured.out
    assert str(doc) in captured.out


def test_main_ignores_files_without_section(tmp_path: Path) -> None:
    doc = tmp_path / "doc.md"
    _write_doc(doc, "# Title\n\nSome text without controls.")

    rc = checker.main([str(doc)])

    assert rc == 0
