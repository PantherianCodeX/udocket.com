from __future__ import annotations

from pathlib import Path

from scripts.docs import check_appendices as ca


def test_expected_fields_include_aliases_and_additional_fields() -> None:
    front_matter = {
        "authors": ["Alice", "Bob"],
        "version": "1.0",
        "status": "draft",
        "classification": "Confidential",
        "last_updated": "2025-01-01",
        "updated_by": "Docs Team",
        "owners": ["Ops"],
        "reviewers": ["QA"],
        "approvers": ["CTO"],
        "approved_by": "CFO",
        "approved_date": "2025-01-02",
        "extra_meta": "Additional context",
    }

    fields = ca.expected_fields(front_matter)

    assert fields["Authors"] == "Alice; Bob"
    assert fields["Updated by"] == "Docs Team"
    assert fields["Approved by"] == "CFO"
    assert fields["Approved date"] == "2025-01-02"
    assert fields["Extra Meta"] == "Additional context"


def _write_doc(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_check_document_accepts_synced_controls(tmp_path: Path) -> None:
    doc = _write_doc(
        tmp_path,
        "appendix.md",
        """---
authors:
  - Alice
version: 1.0
status: draft
classification: Confidential
last_updated: 2025-01-01
updated_by: Docs Team
owners:
  - Ops
reviewers:
  - QA
approvers:
  - CTO
approved_by: CFO
approved_date: 2025-01-02
extra_meta: Additional context
---

## Document Controls

| Field | Value |
| --- | --- |
| Authors | Alice |
| Version | 1.0 |
| Status | draft |
| Classification | Confidential |
| Last updated | 2025-01-01 |
| Updated by | Docs Team |
| Owners | Ops |
| Reviewers | QA |
| Approvers | CTO |
| Approved by | CFO |
| Approved date | 2025-01-02 |
| Extra Meta | Additional context |

Body copy.
""",
    )

    issues = ca.check_document(doc)

    assert issues == []


def test_check_document_flags_mismatched_updated_by(tmp_path: Path) -> None:
    doc = _write_doc(
        tmp_path,
        "appendix_invalid.md",
        """---
authors:
  - Alice
version: 1.0
status: draft
classification: Confidential
last_updated: 2025-01-01
updated_by: Docs Team
owners:
  - Ops
reviewers:
  - QA
approvers:
  - CTO
approved_by: CFO
approved_date: 2025-01-02
---

## Document Controls

| Field | Value |
| --- | --- |
| Authors | Alice |
| Version | 1.0 |
| Status | draft |
| Classification | Confidential |
| Last updated | 2025-01-01 |
| Updated by |  |
| Owners | Ops |
| Reviewers | QA |
| Approvers | CTO |
| Approved by | CFO |
| Approved date | 2025-01-02 |

Body copy.
""",
    )

    issues = ca.check_document(doc)

    assert any("Updated by" in issue for issue in issues)
