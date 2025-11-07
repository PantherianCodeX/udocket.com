from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest

from doc_tools import doc_utils
from doc_tools.sync import document_controls as sdc
from doc_tools.sync.document_controls import (
    OPTIONAL_FIELDS,
    collect_targets,
    parse_args,
    sync_file,
)


DOC_TEMPLATE = """---
author:
  - Alice
  - Bob
version: 0.2
status: implementable
classification: Confidential
last_updated: 2025-10-30
updated_by: Documentation Team
owners:
  - Platform Engineering
reviewers:
  - Documentation Guild
approvers:
  - Architecture Steering Committee
header-includes:
  - test
extra_meta: Extra data
review_notes:
  - Note A
---

## Document controls

| Field | Value |
| --- | --- |
| Authors | Alice |
| Version | 0.1 |
| Status | provisional |
| Classification | Internal |
| Last updated | 2025-10-01 |
| Updated by |  |
| Owners | Platform |
| Reviewers | Doc Guild |
| Approvers | ASC |
| Approved by |  |
| Approved date |  |

Body text.
"""


def _write_doc(tmp_path: Path, content: str = DOC_TEMPLATE, name: str = "service.md") -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def _read_table(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header_idx = lines.index("## Document controls")
    idx = header_idx + 1
    while idx < len(lines):
        stripped = lines[idx].strip()
        if not stripped or stripped.startswith("<!--"):
            idx += 1
            continue
        break
    table_rows: list[str] = []
    while idx < len(lines):
        stripped = lines[idx].strip()
        if not stripped or stripped.startswith("<!--") or not lines[idx].startswith("|"):
            break
        table_rows.append(lines[idx])
        idx += 1
    data_rows = table_rows[2:]
    result: dict[str, str] = {}
    for row in data_rows:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) >= 2:
            result[cells[0]] = cells[1]
    return result


@pytest.fixture(autouse=True)
def _reset_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doc_utils, "yaml", sdc.yaml, raising=False)
    yield


def test_parse_args_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sdc.sys, "argv", ["sync_document_controls.py"])

    args = parse_args()

    assert args.paths == sdc.DEFAULT_ROOTS
    assert args.dry_run is False


def test_collect_targets_handles_dirs(tmp_path: Path) -> None:
    services = tmp_path / "docs" / "src" / "services"
    services.mkdir(parents=True)
    (services / "_template.md").write_text("", encoding="utf-8")
    file_a = services / "a.md"
    file_a.write_text("## Document controls\n| Field | Value |\n| ----- | ----- |\n", encoding="utf-8")

    targets = list(collect_targets([services]))

    assert targets == [file_a.resolve()]


def test_collect_targets_warns_for_missing_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "docs" / "src" / "services"

    targets = list(collect_targets([missing]))

    captured = capsys.readouterr()
    assert targets == []
    assert "does not exist" in captured.err


def test_collect_targets_accepts_file(tmp_path: Path) -> None:
    doc = _write_doc(tmp_path)

    targets = list(collect_targets([doc]))

    assert targets == [doc.resolve()]


def test_sync_updates_document_controls(tmp_path: Path) -> None:
    doc = _write_doc(tmp_path)

    updated = sync_file(doc)

    assert updated is True
    table = _read_table(doc)
    assert table["Authors"] == "Alice; Bob"
    assert table["Version"] == "0.2"
    assert table["Status"] == "implementable"
    assert table["Classification"] == "Confidential"
    assert table["Last updated"] == "2025-10-30"
    assert table["Updated by"] == "Documentation Team"
    assert table["Owners"] == "Platform Engineering"
    assert table["Reviewers"] == "Documentation Guild"
    assert table["Approvers"] == "Architecture Steering Committee"
    assert table["Extra Meta"] == "Extra data"
    assert table["Review Notes"] == "Note A"
    assert "Header Includes" not in table
    for optional in OPTIONAL_FIELDS:
        assert table[optional] == ""


def test_sync_no_changes_when_table_matches(tmp_path: Path) -> None:
    content = """---
author:
  - Alice
  - Bob
version: 0.2
status: implementable
classification: Confidential
last_updated: 2025-10-30
updated_by: Documentation Team
owners:
  - Platform Engineering
reviewers:
  - Documentation Guild
approvers:
  - Architecture Steering Committee
header-includes:
  - test
extra_meta: Extra data
review_notes:
  - Note A
---

## Document controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Alice; Bob |
| Version | 0.2 |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-30 |
| Updated by | Documentation Team |
| Owners | Platform Engineering |
| Reviewers | Documentation Guild |
| Approvers | Architecture Steering Committee |
| Approved by |  |
| Approved date |  |
| Extra Meta | Extra data |
| Review Notes | Note A |
<!-- END AUTO-GENERATED: document-controls -->

Body text.
"""
    doc = _write_doc(tmp_path, content=content)

    updated = sync_file(doc)

    assert updated is False


def test_sync_skips_missing_front_matter(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doc = _write_doc(tmp_path, content="## Document controls\n| Field | Value |\n| ----- | ----- |\n")

    updated = sync_file(doc)

    captured = capsys.readouterr()
    assert updated is False
    assert "missing usable front matter" in captured.err


def test_sync_rebuilds_sparse_table(tmp_path: Path) -> None:
    content = """---
author: Alice
---

## Document controls

| Field | Value |
| ----- | ----- |
| Authors | Alice |
"""
    doc = _write_doc(tmp_path, content=content)

    updated = sync_file(doc)

    assert updated is True
    table = _read_table(doc)
    assert table["Authors"] == "Alice"
    assert table["Version"] == ""
    assert table["Updated by"] == ""
    assert "Approvers" in table


def test_sync_skips_when_table_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    content = """---
author: Alice
---

## Document controls

No table present.
"""
    doc = _write_doc(tmp_path, content=content)

    updated = sync_file(doc)

    captured = capsys.readouterr()
    assert updated is False
    assert "incomplete document controls table" in captured.err


def test_sync_dry_run_reports_without_writing(tmp_path: Path) -> None:
    doc = _write_doc(tmp_path)
    original = doc.read_text(encoding="utf-8")

    updated = sync_file(doc, dry_run=True)

    assert updated is True
    assert doc.read_text(encoding="utf-8") == original


def test_sync_skips_when_section_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    content = """---
author: Alice
---

## Another heading

Body text.
"""
    doc = _write_doc(tmp_path, content=content)

    updated = sync_file(doc)

    captured = capsys.readouterr()
    assert updated is False
    assert "missing 'Document controls' section" in captured.err


def test_sync_warns_when_marker_end_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    content = """---
author: Alice
---

## Document controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Alice |
"""
    doc = _write_doc(tmp_path, content=content)

    updated = sync_file(doc)

    captured = capsys.readouterr()
    assert updated is False
    assert "missing '<!-- END AUTO-GENERATED: document-controls -->'" in captured.err


def test_sync_warns_when_table_rows_insufficient(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    content = """---
author: Alice
---

## Document controls

| Field | Value |
"""
    doc = _write_doc(tmp_path, content=content)

    updated = sync_file(doc)

    captured = capsys.readouterr()
    assert updated is False
    assert "incomplete document controls table" in captured.err


def test_sync_inserts_missing_rows(tmp_path: Path) -> None:
    content = """---
author:
  - Alice
version: 0.2
status: implementable
classification: Confidential
last_updated: 2025-10-30
updated_by: Documentation Team
owners:
  - Platform Engineering
reviewers:
  - Documentation Guild
approvers:
  - Architecture Steering Committee
---

## Document controls

| Field | Value |
| ----- | ----- |
| Authors | Alice |
| Version | 0.2 |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-30 |
| Owners | Platform Engineering |
| Approvers | Architecture Steering Committee |

Body text.
"""
    doc = _write_doc(tmp_path, content=content)

    updated = sync_file(doc)

    assert updated is True
    table = _read_table(doc)
    assert table["Reviewers"] == "Documentation Guild"
    assert table["Updated by"] == "Documentation Team"
    assert "Approvers" in table


def test_sync_warns_when_unexpected_rows_present(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    content = """---
author: Alice
---

## Document controls

| Field | Value |
| ----- | ----- |
| Authors | Alice |
| Custom Field | Keep me |
"""
    doc = _write_doc(tmp_path, content=content)

    updated = sync_file(doc)

    captured = capsys.readouterr()
    assert updated is False
    assert "unexpected rows" in captured.err


def test_main_handles_no_targets(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sdc, "parse_args", lambda argv=None: argparse.Namespace(paths=[Path("/nope")], dry_run=False))
    monkeypatch.setattr(sdc, "collect_targets", lambda paths: iter([]))

    def _fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("should not run")

    monkeypatch.setattr(sdc.subprocess, "run", _fail)

    rc = sdc.main()

    captured = capsys.readouterr()
    assert rc == 0
    assert "no markdown targets found" in captured.err


def test_main_aborts_without_yaml(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doc = _write_doc(tmp_path)
    monkeypatch.setattr(sdc, "parse_args", lambda argv=None: argparse.Namespace(paths=[doc], dry_run=False))
    monkeypatch.setattr(sdc, "collect_targets", lambda paths: iter([doc]))
    monkeypatch.setattr(sdc, "yaml", None)

    def _fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("should not run")

    monkeypatch.setattr(sdc.subprocess, "run", _fail)

    rc = sdc.main()

    captured = capsys.readouterr()
    assert rc == 0
    assert "PyYAML not available" in captured.err


def test_main_runs_and_updates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doc = _write_doc(tmp_path)
    monkeypatch.setattr(sdc, "parse_args", lambda argv=None: argparse.Namespace(paths=[doc], dry_run=False))
    monkeypatch.setattr(sdc, "collect_targets", lambda paths: iter([doc]))
    calls: list[tuple[list[str], dict[str, object]]] = []

    def _fake_run(cmd: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append((cmd, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(sdc.subprocess, "run", _fake_run)

    rc = sdc.main()

    captured = capsys.readouterr()
    assert rc == 0
    assert calls
    assert "--frontmatter" in calls[0][0]
    assert calls[0][0][-1] == str(doc.resolve())
    assert calls[0][1]["cwd"] == str(sdc.PROJECT_ROOT)
    assert "completed (1 file(s) updated)" in captured.out


def test_main_returns_failure_when_verification_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    doc = _write_doc(tmp_path)
    monkeypatch.setattr(sdc, "parse_args", lambda argv=None: argparse.Namespace(paths=[doc], dry_run=False))
    monkeypatch.setattr(sdc, "collect_targets", lambda paths: iter([doc]))

    def _fake_run(cmd: list[str], **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=2)

    monkeypatch.setattr(sdc.subprocess, "run", _fake_run)

    rc = sdc.main()

    captured = capsys.readouterr()
    assert rc == 2
    assert "verification via check_structure failed" in captured.err
