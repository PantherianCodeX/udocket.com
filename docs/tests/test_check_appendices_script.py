from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent

import pytest

from docs.tools import check_appendices as ca


BASE_FRONT_MATTER = [
    "title: Example Appendix",
    "subtitle: Example subtitle",
    "authors:",
    "  - Alice",
    "version: 1.0",
    "status: draft",
    "classification: Confidential",
    "last_updated: 2025-01-01",
    "updated_by: Alice",
    "owners:",
    "  - Team",
    "reviewers:",
    "  - Reviewer",
    "approvers:",
    "  - Approver",
    "approved_by:",
    "approved_date:",
]

BASE_TABLE = [
    "## Document Controls",
    "",
    "| Field | Value |",
    "| --- | --- |",
    "| Authors | Alice |",
    "| Version | 1.0 |",
    "| Status | draft |",
    "| Classification | Confidential |",
    "| Last updated | 2025-01-01 |",
    "| Updated by | Alice |",
    "| Owners | Team |",
    "| Reviewers | Reviewer |",
    "| Approvers | Approver |",
    "| Approved by |  |",
    "| Approved date |  |",
]


def build_doc(
    *,
    front_extra: list[str] | None = None,
    table_extra: list[str] | None = None,
    omit_table_rows: list[str] | None = None,
) -> str:
    lines: list[str] = ["---", *BASE_FRONT_MATTER]
    if front_extra:
        lines.extend(front_extra)
    lines.append("---")
    lines.append("")
    lines.extend(BASE_TABLE)
    if omit_table_rows:
        omit_set = set(omit_table_rows)
        lines = [
            line for line in lines if not (line.startswith("|") and line in omit_set)
        ]
    if table_extra:
        lines.extend(table_extra)
    lines.append("")
    return "\n".join(lines)


def write_doc(tmp_path: Path, content: str, name: str = "appendix.md") -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_collect_targets_skips_templates(tmp_path: Path) -> None:
    root = tmp_path / "appendices"
    root.mkdir()
    template = root / "_template.md"
    template.write_text("template", encoding="utf-8")
    doc = root / "api.md"
    doc.write_text(build_doc(), encoding="utf-8")

    targets = list(ca.collect_targets([root]))

    assert targets == [doc.resolve()]


def test_collect_targets_warns_missing_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "missing"

    targets = list(ca.collect_targets([missing]))

    assert targets == []
    assert "does not exist" in capsys.readouterr().err


def test_expected_fields_adds_custom_keys() -> None:
    front_matter = {line.split(":")[0]: "value" for line in BASE_FRONT_MATTER if ":" in line}
    front_matter["custom_key"] = "Custom Value"

    fields = ca.expected_fields(front_matter)

    assert fields["Custom Key"] == "Custom Value"


def test_locate_document_controls_missing_header() -> None:
    lines = ["---", "---", "Body"]

    assert ca.locate_document_controls(lines) is None


def test_check_document_valid(tmp_path: Path) -> None:
    doc = write_doc(tmp_path, build_doc())

    issues = ca.check_document(doc)

    assert issues == []


def test_check_document_missing_front_matter(tmp_path: Path) -> None:
    doc = write_doc(tmp_path, "No front matter")

    issues = ca.check_document(doc)

    assert any("missing or invalid front matter" in issue for issue in issues)


def test_check_document_missing_controls_section(tmp_path: Path) -> None:
    content = dedent(
        """---
        title: Example Appendix
        ---

        Body content
        """
    )
    doc = write_doc(tmp_path, content)

    issues = ca.check_document(doc)

    assert any("missing '## Document Controls'" in issue for issue in issues)


def test_check_document_incomplete_table(tmp_path: Path) -> None:
    content = build_doc()
    partial = content.split("## Document Controls")[0] + "## Document Controls\n| Field | Value |\n"
    doc = write_doc(tmp_path, partial)

    issues = ca.check_document(doc)

    assert any("table incomplete" in issue for issue in issues)


def test_check_document_missing_field_detected(tmp_path: Path) -> None:
    content = build_doc(omit_table_rows=["| Owners | Team |"])
    doc = write_doc(tmp_path, content)

    issues = ca.check_document(doc)

    assert any("missing field 'Owners'" in issue for issue in issues)


def test_check_document_mismatched_value(tmp_path: Path) -> None:
    content = build_doc().replace("| Authors | Alice |", "| Authors | Bob |")
    doc = write_doc(tmp_path, content)

    issues = ca.check_document(doc)

    assert any("does not match front matter" in issue for issue in issues)


def test_check_document_unexpected_field(tmp_path: Path) -> None:
    content = build_doc(table_extra=["| Surprise | Value |"])
    doc = write_doc(tmp_path, content)

    issues = ca.check_document(doc)

    assert any("unexpected field 'Surprise'" in issue for issue in issues)


def test_check_document_optional_fields_allow_blank(tmp_path: Path) -> None:
    doc = write_doc(tmp_path, build_doc())

    issues = ca.check_document(doc)

    assert issues == []


def test_check_document_requires_custom_field_row(tmp_path: Path) -> None:
    content = build_doc(front_extra=["custom_field: Present"])
    doc = write_doc(tmp_path, content)

    issues = ca.check_document(doc)

    assert any("missing field 'Custom Field'" in issue for issue in issues)


def test_main_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doc = write_doc(tmp_path, build_doc())
    monkeypatch.setattr(ca, "parse_args", lambda: argparse.Namespace(paths=[doc]))

    rc = ca.main()

    captured = capsys.readouterr()
    assert rc == 0
    assert "synced front matter and document controls" in captured.out


def test_main_reports_issues(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doc = write_doc(tmp_path, "invalid")
    monkeypatch.setattr(ca, "parse_args", lambda: argparse.Namespace(paths=[doc]))

    rc = ca.main()

    captured = capsys.readouterr()
    assert rc == 1
    assert "missing or invalid front matter" in captured.out


def test_main_requires_yaml(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doc = write_doc(tmp_path, build_doc())
    monkeypatch.setattr(ca, "parse_args", lambda: argparse.Namespace(paths=[doc]))
    monkeypatch.setattr(ca.doc_utils, "yaml", None)

    rc = ca.main()

    captured = capsys.readouterr()
    assert rc == 1
    assert "PyYAML is required" in captured.err


def test_main_no_targets(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        ca,
        "parse_args",
        lambda: argparse.Namespace(paths=[Path("missing")]),
    )

    rc = ca.main()

    captured = capsys.readouterr()
    assert rc == 1
    assert "no markdown targets found" in captured.err
