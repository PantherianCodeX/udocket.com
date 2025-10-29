from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pytest

from scripts.docs import check_structure as cs
from scripts.docs.check_structure import (
    SectionSpec,
    build_template_spec,
    check_document_controls,
    extract_numbering,
    gather_preamble,
    main as cs_main,
    parse_args as cs_parse_args,
    parse_front_matter,
    parse_sections,
    _stringify,
    validate_sections,
    walk_targets,
)


TEMPLATE_CONTENT = """## 1) Purpose
**Purpose:** Template **|**
**Contract:** Template **|**
**State:** Template **|**
**Failures & handling:** Template **|**
**Observability:** Template **|**
**Breadcrumbs:** Template **|**
**References:** Template **|**

## 2) Responsibilities
**Purpose:** Template **|**
**Contract:** Template **|**
**State:** Template **|**
**Failures & handling:** Template **|**
**Observability:** Template **|**
**Breadcrumbs:** Template **|**
**References:** Template **|**

## 3) Extras

Body text.
"""


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture()
def template_path(tmp_path: Path) -> Path:
    return _write(tmp_path / "_template.md", TEMPLATE_CONTENT)

def test_parse_args_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cs.sys, "argv", ["check_structure.py"])

    args = cs_parse_args()

    assert args.paths == [Path("docs/src/services")]
    assert args.template is None


def test_find_template_override_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        cs.find_template(tmp_path, tmp_path / "missing.md")


def test_extract_numbering_variants() -> None:
    assert extract_numbering("1) Heading") == (1,)
    assert extract_numbering("2.3 Title") == (2, 3)
    assert extract_numbering("Heading") is None


def test_parse_sections_and_preamble_normalisation() -> None:
    markdown = """## 1) Section
**failure mode & handling:** Example **|**
Paragraph text.

## Heading
"""
    sections = parse_sections(markdown)
    assert sections == [((1,), 2, "1) Section", 1)]
    lines = markdown.splitlines()
    entries = gather_preamble(lines, 1)
    assert entries[0][1] == "Failures & handling"


def test_parse_front_matter_invalid_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    lines = ["---", "key: [", "---"]
    monkeypatch.setitem(sys.modules, "yaml", __import__("yaml"))

    assert parse_front_matter(lines) == {}


def test_stringify_handles_structured_values(monkeypatch: pytest.MonkeyPatch) -> None:
    yaml = __import__("yaml")
    monkeypatch.setitem(sys.modules, "yaml", yaml)

    result = _stringify({"a": 1, "b": 2})

    assert "a: 1" in result
    assert "; " in result


def test_walk_targets_skips_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "missing"

    targets = list(walk_targets([missing]))

    assert targets == []
    assert "does not exist" in capsys.readouterr().err


def _write_service_doc(path: Path) -> Path:
    content = """---
author: Alice
version: 1.0
status: draft
classification: Internal
last_updated: 2025-01-01
owners:
  - Team
reviewers:
  - Rev
approvers:
  - Approver
---

## Document Controls

| Field | Value |
| ----- | ----- |
| Authors | Alice |
| Version | 1.0 |
| Status | draft |
| Classification | Internal |
| Last updated | 2025-01-01 |
| Owners | Team |
| Reviewers | Rev |
| Approvers | Approver |
| Approved by |  |
| Approved date |  |

## 1) Purpose
**Purpose:** Template **|**
**Contract:** Template **|**
**State:** Template **|**
**Failures & handling:** Template **|**
**Observability:** Template **|**
**Breadcrumbs:** Template **|**
**References:** Template **|**

## 2) Responsibilities
**Purpose:** Template **|**
**Contract:** Template **|**
**State:** Template **|**
**Failures & handling:** Template **|**
**Observability:** Template **|**
**Breadcrumbs:** Template **|**
**References:** Template **|**

## 3) Extras
Body text.
"""
    path.write_text(content, encoding="utf-8")
    return path


def test_main_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    services = tmp_path / "docs" / "src" / "services"
    services.mkdir(parents=True)
    template = services / "_template.md"
    template.write_text(TEMPLATE_CONTENT, encoding="utf-8")
    doc = _write_service_doc(services / "service.md")

    monkeypatch.setattr(cs, "parse_args", lambda: argparse.Namespace(paths=[doc], template=None))

    rc = cs_main()

    captured = capsys.readouterr()
    assert rc == 0
    assert "All service specifications comply" in captured.out


def test_main_reports_issues(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    services = tmp_path / "docs" / "src" / "services"
    services.mkdir(parents=True)
    template = services / "_template.md"
    template.write_text(TEMPLATE_CONTENT, encoding="utf-8")
    doc = services / "service.md"
    doc.write_text("---\n---\n\n## Document Controls\n| Field | Value |\n| ----- | ----- |\n", encoding="utf-8")

    monkeypatch.setattr(cs, "parse_args", lambda: argparse.Namespace(paths=[services], template=None))

    rc = cs_main()

    captured = capsys.readouterr()
    assert rc == 1
    assert "document controls table incomplete" in captured.out


def test_heading_mismatch_detected(tmp_path: Path, template_path: Path) -> None:
    specs = build_template_spec(template_path)
    doc = _write(
        tmp_path / "service.md",
        """## 1) Mission Statement
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 3) Extras
Body text.
""",
    )

    errors = validate_sections(doc, specs, doc.read_text(encoding="utf-8").splitlines())

    assert any("section 1 heading '1) Mission Statement' does not match template '1) Purpose'" in err for err in errors)


def test_heading_level_mismatch_detected(tmp_path: Path, template_path: Path) -> None:
    specs = build_template_spec(template_path)
    doc = _write(
        tmp_path / "service.md",
        """## 1) Purpose
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

### 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 3) Extras
Body text.
""",
    )

    errors = validate_sections(doc, specs, doc.read_text(encoding="utf-8").splitlines())

    assert any("section 2 uses heading level 3 but template requires 2" in err for err in errors)


def test_structure_validation_passes_with_matching_headings(tmp_path: Path, template_path: Path) -> None:
    specs = build_template_spec(template_path)
    doc = _write(
        tmp_path / "service.md",
        """## 1) Purpose
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 3) Extras
Body text.
""",
    )

    errors = validate_sections(doc, specs, doc.read_text(encoding="utf-8").splitlines())

    assert errors == []


def test_structure_validation_allows_binding_suffix(tmp_path: Path, template_path: Path) -> None:
    specs = build_template_spec(template_path)
    doc = _write(
        tmp_path / "service.md",
        """## 1) Purpose (binding)
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 2) Responsibilities (informative)
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 3) Extras
Body text.
""",
    )

    errors = validate_sections(doc, specs, doc.read_text(encoding="utf-8").splitlines())

    assert errors == []


def test_structure_validation_rejects_unknown_suffix(tmp_path: Path, template_path: Path) -> None:
    specs = build_template_spec(template_path)
    doc = _write(
        tmp_path / "service.md",
        """## 1) Purpose (draft)
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 3) Extras
Body text.
""",
    )

    errors = validate_sections(doc, specs, doc.read_text(encoding="utf-8").splitlines())

    assert any("heading '1) Purpose (draft)' does not match template '1) Purpose'" in err for err in errors)


def test_title_case_allows_acronyms(tmp_path: Path, template_path: Path) -> None:
    specs = build_template_spec(template_path)
    doc = _write(
        tmp_path / "service.md",
        """## 1) Purpose & SLOs
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 3) Extras
Body text.
""",
    )

    errors = validate_sections(doc, specs, doc.read_text(encoding="utf-8").splitlines())

    assert any("does not match template" in err for err in errors)
    assert not any("Title Case" in err for err in errors)


def test_title_case_rejects_lowercase_word(tmp_path: Path, template_path: Path) -> None:
    specs = build_template_spec(template_path)
    doc = _write(
        tmp_path / "service.md",
        """## 1) purpose section
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 3) Extras
Body text.
""",
    )

    errors = validate_sections(doc, specs, doc.read_text(encoding="utf-8").splitlines())

    assert any("must use Title Case" in err for err in errors)


def test_preamble_missing_entry_detected(tmp_path: Path, template_path: Path) -> None:
    specs = build_template_spec(template_path)
    doc = _write(
        tmp_path / "service.md",
        """## 1) Purpose
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 3) Extras
Body text.
""",
    )

    errors = validate_sections(doc, specs, doc.read_text(encoding="utf-8").splitlines())

    assert any("missing preamble entries" in err for err in errors)


def test_preamble_extra_entry_detected(tmp_path: Path, template_path: Path) -> None:
    specs = build_template_spec(template_path)
    doc = _write(
        tmp_path / "service.md",
        """## 1) Purpose
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**
**Extra:** Doc **|**

## 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 3) Extras
Body text.
""",
    )

    errors = validate_sections(doc, specs, doc.read_text(encoding="utf-8").splitlines())

    assert any("unexpected preamble entries" in err for err in errors)


def test_preamble_requires_marker(tmp_path: Path, template_path: Path) -> None:
    specs = build_template_spec(template_path)
    doc = _write(
        tmp_path / "service.md",
        """## 1) Purpose
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 3) Extras
Body text.
""",
    )

    errors = validate_sections(doc, specs, doc.read_text(encoding="utf-8").splitlines())

    assert any("must end with '**|**'" in err for err in errors)


def test_no_preamble_allowed(tmp_path: Path, template_path: Path) -> None:
    specs = build_template_spec(template_path)
    doc = _write(
        tmp_path / "service.md",
        """## 1) Purpose
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc **|**

## 3) Extras
**Purpose:** Should not be here **|**
Body text.
""",
    )

    errors = validate_sections(doc, specs, doc.read_text(encoding="utf-8").splitlines())

    assert any("should not have preamble entries" in err for err in errors)


def test_document_controls_additional_fields_valid() -> None:
    lines = [
        "---",
        "author:",
        "  - Alice",
        "version: 1.0",
        "status: draft",
        "classification: Confidential",
        "last_updated: 2025-10-30",
        "owners:",
        "  - Team",
        "reviewers:",
        "  - Reviewer",
        "approvers:",
        "  - Approver",
        "extra_meta: Extra data",
        "---",
        "## Document controls",
        "| Field | Value |",
        "| ----- | ----- |",
        "| Authors | Alice |",
        "| Version | 1.0 |",
        "| Status | draft |",
        "| Classification | Confidential |",
        "| Last updated | 2025-10-30 |",
        "| Owners | Team |",
        "| Reviewers | Reviewer |",
        "| Approvers | Approver |",
        "| Approved by |  |",
        "| Approved date |  |",
        "| Extra Meta | Extra data |",
    ]

    errors = check_document_controls(Path("service.md"), lines)

    assert errors == []


def test_document_controls_additional_field_missing_row_detected() -> None:
    lines = [
        "---",
        "author: Alice",
        "version: 1.0",
        "status: draft",
        "classification: Confidential",
        "last_updated: 2025-10-30",
        "owners: Team",
        "reviewers: Reviewer",
        "approvers: Approver",
        "extra_meta: Extra data",
        "---",
        "## Document controls",
        "| Field | Value |",
        "| ----- | ----- |",
        "| Authors | Alice |",
        "| Version | 1.0 |",
        "| Status | draft |",
        "| Classification | Confidential |",
        "| Last updated | 2025-10-30 |",
        "| Owners | Team |",
        "| Reviewers | Reviewer |",
        "| Approvers | Approver |",
        "| Approved by |  |",
        "| Approved date |  |",
    ]

    errors = check_document_controls(Path("service.md"), lines)

    assert any("Extra Meta" in err for err in errors)


def test_document_controls_unexpected_field_detected() -> None:
    lines = [
        "---",
        "author: Alice",
        "version: 1.0",
        "status: draft",
        "classification: Confidential",
        "last_updated: 2025-10-30",
        "owners: Team",
        "reviewers: Reviewer",
        "approvers: Approver",
        "---",
        "## Document controls",
        "| Field | Value |",
        "| ----- | ----- |",
        "| Authors | Alice |",
        "| Version | 1.0 |",
        "| Status | draft |",
        "| Classification | Confidential |",
        "| Last updated | 2025-10-30 |",
        "| Owners | Team |",
        "| Reviewers | Reviewer |",
        "| Approvers | Approver |",
        "| Approved by |  |",
        "| Approved date |  |",
        "| Custom Field | 123 |",
    ]

    errors = check_document_controls(Path("service.md"), lines)

    assert any("unexpected field 'Custom Field'" in err for err in errors)


def test_document_controls_missing_field_detected() -> None:
    lines = [
        "---",
        "title: Sample",
        "version: 1.0",
        "status: draft",
        "classification: Confidential",
        "last_updated: 2025-01-01",
        "owners:",
        "  - Owner Team",
        "reviewers:",
        "  - Reviewer",
        "approvers:",
        "  - Approver",
        "---",
        "",
        "## Document controls",
        "",
        "| Field | Value |",
        "| ----- | ----- |",
        "| Authors | |",
        "| Version | 1.0 |",
        "| Status | draft |",
        "| Classification | Confidential |",
        "| Last updated | 2025-01-01 |",
        "| Owners | Owner Team |",
        "| Reviewers | Reviewer |",
        "| Approvers | Approver |",
        "| Approved by | |",
        "| Approved date | |",
    ]

    errors = check_document_controls(Path("service.md"), lines)

    assert any("Authors" in err for err in errors)


def test_document_controls_mismatch_detected() -> None:
    lines = [
        "---",
        "author: Author Name",
        "version: 1.0",
        "status: draft",
        "classification: Confidential",
        "last_updated: 2025-01-01",
        "owners:",
        "  - Owner Team",
        "reviewers:",
        "  - Reviewer",
        "approvers:",
        "  - Approver",
        "---",
        "## Document controls",
        "| Field | Value |",
        "| ----- | ----- |",
        "| Authors | Someone Else |",
        "| Version | 1.0 |",
        "| Status | draft |",
        "| Classification | Confidential |",
        "| Last updated | 2025-01-01 |",
        "| Owners | Owner Team |",
        "| Reviewers | Reviewer |",
        "| Approvers | Approver |",
        "| Approved by | |",
        "| Approved date | |",
    ]

    errors = check_document_controls(Path("service.md"), lines)

    assert any("Authors" in err for err in errors)


def test_document_controls_optional_fields_blank() -> None:
    lines = [
        "---",
        "author: Author Name",
        "version: 1.0",
        "status: draft",
        "classification: Confidential",
        "last_updated: 2025-01-01",
        "owners:",
        "  - Owner Team",
        "reviewers:",
        "  - Reviewer",
        "approvers:",
        "  - Approver",
        "---",
        "## Document controls",
        "| Field | Value |",
        "| ----- | ----- |",
        "| Authors | Author Name |",
        "| Version | 1.0 |",
        "| Status | draft |",
        "| Classification | Confidential |",
        "| Last updated | 2025-01-01 |",
        "| Owners | Owner Team |",
        "| Reviewers | Reviewer |",
        "| Approvers | Approver |",
        "| Approved by | |",
        "| Approved date | |",
    ]

    errors = check_document_controls(Path("service.md"), lines)

    assert errors == []
