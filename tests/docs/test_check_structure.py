from __future__ import annotations

from pathlib import Path

import pytest

from scripts.docs.check_structure import (
    build_template_spec,
    check_document_controls,
    validate_sections,
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
