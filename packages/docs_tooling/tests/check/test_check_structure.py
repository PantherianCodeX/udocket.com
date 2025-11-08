from __future__ import annotations

import argparse
from pathlib import Path
import sys
from textwrap import dedent
from typing import Callable, List

import pytest

from doc_tools.check import structure as cs
from doc_tools.common import doc_utils
from doc_tools.check.structure import (
    SectionSpec,
    TableRowSpec,
    TableSpec,
    build_front_matter_index,
    build_template_spec,
    check_document_controls,
    ensure_template_requirements,
    extract_tables,
    extract_numbering,
    find_section_header,
    gather_preamble,
    main as cs_main,
    parse_args as cs_parse_args,
    parse_table,
    parse_sections,
    validate_sections,
    walk_targets,
)


TEMPLATE_CONTENT = """---
title: Template
subtitle: Example Template
author: Template Author
version: 0.1
status: draft
classification: Internal
last_updated: 2025-01-01
updated_by: Template Author
owners:
  - Template Team
reviewers:
  - Template Reviewer
approvers:
  - Template Approver
approved_by: 
approved_date: 
---

## Document Controls

| Field | Value |
| --- | --- |
| Authors | Template Author |
| Version | 0.1 |
| Status | draft |
| Classification | Internal |
| Last updated | 2025-01-01 |
| Updated by | Template Author |
| Owners | Template Team |
| Reviewers | Template Reviewer |
| Approvers | Template Approver |
| Approved by |  |
| Approved date |  |

## 1) Purpose
**Purpose:** Template **|**
**Contract:** Template **|**
**State:** Template **|**
**Failures & handling:** Template **|**
**Observability:** Template **|**
**Breadcrumbs:** Template **|**
**References:** Template
## 2) Responsibilities
**Purpose:** Template **|**
**Contract:** Template **|**
**State:** Template **|**
**Failures & handling:** Template **|**
**Observability:** Template **|**
**Breadcrumbs:** Template **|**
**References:** Template
## 3) Extras

Body text.

### 3.3 API Error Codes (binding)

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `FOO` | Something happened | Do a thing |

```yaml
error_codes:
  - code: "<CODE>"
    http_status: "<STATUS>"
    audit_required: "<true|false>"
    description: "<Description>"
    client_action: "<Guidance>"
    related_metrics: [optional]
```
"""


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _strip_yaml_block(content: str) -> str:
    lines = content.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip().startswith("```yaml"))
    except StopIteration:
        return content
    end = start + 1
    while end < len(lines) and not lines[end].strip().startswith("```"):
        end += 1
    if end < len(lines):
        del lines[start : end + 1]
    else:
        del lines[start:]
    return "\n".join(lines)


def _edit_yaml_block(content: str, transform: Callable[[List[str]], List[str]]) -> str:
    lines = content.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip().startswith("```yaml"))
    except StopIteration:
        return content
    end = start + 1
    while end < len(lines) and not lines[end].strip().startswith("```"):
        end += 1
    block = lines[start + 1 : end]
    new_block = transform(block)
    lines = lines[: start + 1] + new_block + lines[end:]
    return "\n".join(lines)


@pytest.fixture()
def template_path(tmp_path: Path) -> Path:
    return _write(tmp_path / "_template.md", TEMPLATE_CONTENT)

def test_parse_args_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cs.sys, "argv", ["check_structure.py"])

    args = cs_parse_args()

    assert args.paths == [cs.paths.DOCS_ROOT]
    assert args.template is None
    assert args.frontmatter is False


def test_parse_args_frontmatter_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cs.sys, "argv", ["check_structure.py", "--frontmatter"])

    args = cs_parse_args()

    assert args.frontmatter is True


def test_find_template_override_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        cs.find_template(tmp_path, tmp_path / "missing.md")


def test_find_template_search_failure(tmp_path: Path) -> None:
    target = tmp_path / "docs" / "src"
    target.mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        cs.find_template(target, None)


def test_find_section_header_missing_raises() -> None:
    with pytest.raises(ValueError):
        cs.find_section_header(["## Intro"], "## Missing")


def test_extract_numbering_variants() -> None:
    assert extract_numbering("1) Heading") == (1,)
    assert extract_numbering("2.3 Title") == (2, 3)
    assert extract_numbering("3.1.4 Title") == (3, 1, 4)
    assert extract_numbering("Heading") is None


def test_parse_table_requires_minimum_rows() -> None:
    with pytest.raises(ValueError):
        parse_table(["| Field | Value |"])


def test_parse_table_discards_incomplete_data_row() -> None:
    header, separator, rows = parse_table([
        "| Field | Value |",
        "| --- | --- |",
        "| OnlyField |",
    ])

    assert header.startswith("| Field")
    assert rows == []


def test_extract_tables_skips_incomplete_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cs,
        "iter_markdown_tables",
        lambda segment, allow_optional_tags: [(0, ["header", "separator", "row"])],
    )
    monkeypatch.setattr(cs, "split_table_row", lambda raw: [] if raw == "header" else [])

    tables = extract_tables(["dummy"], 0, 1, allow_optional_tags=False)

    assert tables == []


def test_extract_tables_ignores_short_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cs, "iter_markdown_tables", lambda segment, allow_optional_tags: [(0, ["header"])])

    tables = extract_tables(["dummy"], 0, 1, allow_optional_tags=False)

    assert tables == []


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
    assert entries[0][1] == "failure mode & handling"


def test_build_front_matter_index_injects_primary(monkeypatch: pytest.MonkeyPatch) -> None:
    original = cs.key_variants

    def fake_key_variants(value: str) -> Tuple[str, ...]:
        return ("alias",)

    monkeypatch.setattr(cs, "key_variants", fake_key_variants)
    index = cs.build_front_matter_index({"Custom Key": "value"})
    assert "custom_key" in index
    monkeypatch.setattr(cs, "key_variants", original)


def test_build_front_matter_index_skips_empty_variants(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cs, "key_variants", lambda value: ("", "alias"))

    index = build_front_matter_index({"Example": "value"})

    assert index == {"example": ["Example"], "alias": ["Example"]}


def test_template_disabled_detection(tmp_path: Path) -> None:
    empty_template = tmp_path / "_template.md"
    empty_template.write_text("", encoding="utf-8")
    assert cs.template_disabled(empty_template)

    marker_template = tmp_path / "marker_template.md"
    marker_template.write_text("<!-- template:disabled -->", encoding="utf-8")
    assert cs.template_disabled(marker_template)


def test_parse_front_matter_invalid_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    lines = ["---", "key: [", "---"]
    monkeypatch.setitem(sys.modules, "yaml", __import__("yaml"))

    with pytest.raises(Exception):
        doc_utils.parse_front_matter(lines)


def test_stringify_handles_structured_values(monkeypatch: pytest.MonkeyPatch) -> None:
    yaml = __import__("yaml")
    monkeypatch.setitem(sys.modules, "yaml", yaml)

    result = doc_utils.stringify({"a": 1, "b": 2})

    assert "a: 1" in result
    assert "; " in result


def test_walk_targets_skips_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "missing"

    targets = list(walk_targets([missing]))

    assert targets == []
    assert "does not exist" in capsys.readouterr().err


def _write_service_doc(path: Path) -> Path:
    content = """---
title: Sample Service
subtitle: Example subtitle
author: Alice
version: 1.0
status: draft
classification: Internal
last_updated: 2025-01-01
updated_by: Alice
owners:
  - Team
reviewers:
  - Rev
approvers:
  - Approver
approved_by: 
approved_date: 
---

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| ----- | ----- |
| Authors | Alice |
| Version | 1.0 |
| Status | draft |
| Classification | Internal |
| Last updated | 2025-01-01 |
| Updated by | Alice |
| Owners | Team |
| Reviewers | Rev |
| Approvers | Approver |
| Approved by |  |
| Approved date |  |
<!-- END AUTO-GENERATED: document-controls -->

## 1) Purpose
**Purpose:** Template **|**
**Contract:** Template **|**
**State:** Template **|**
**Failures & handling:** Template **|**
**Observability:** Template **|**
**Breadcrumbs:** Template **|**
**References:** Template
## 2) Responsibilities
**Purpose:** Template **|**
**Contract:** Template **|**
**State:** Template **|**
**Failures & handling:** Template **|**
**Observability:** Template **|**
**Breadcrumbs:** Template **|**
**References:** Template
## 3) Extras
Body text.
### 3.3 API Error Codes (binding)
| Code | Scenario | Client guidance |
| --- | --- | --- |
| `FOO` | Something happened | Do a thing |

```yaml
error_codes:
  - code: FOO
    http_status: 400
    audit_required: false
    description: Something happened
    client_action: Do a thing
```
"""
    path.write_text(content, encoding="utf-8")
    return path


def test_extract_tables_optional_rows() -> None:
    lines = [
        "| Col | Value |",
        "| --- | --- |",
        "| foo | bar |",
        "| [optional] baz | qux |",
    ]

    tables = cs.extract_tables(lines, 0, len(lines), allow_optional_tags=True)

    assert len(tables) == 1
    assert tables[0].rows[0].first_cell == "foo"
    assert tables[0].rows[1].first_cell == "baz"
    assert tables[0].rows[1].optional is True


def test_find_template_override_success(tmp_path: Path) -> None:
    override = tmp_path / "override.md"
    override.write_text("template", encoding="utf-8")

    resolved = cs.find_template(tmp_path, override)

    assert resolved == override.resolve()


def test_build_template_spec_handles_trailing_heading(tmp_path: Path) -> None:
    template = tmp_path / "_template.md"
    template.write_text("## 1) Section\n**Purpose:** Text\n", encoding="utf-8")

    specs = cs.build_template_spec(template)

    assert specs[0].title.strip().startswith("1) Section")


def test_template_with_trailing_divider_rejected(tmp_path: Path) -> None:
    template = TEMPLATE_CONTENT.replace("**References:** Template", "**References:** Template **|**")
    template_path = _write(tmp_path / "_template.md", template)

    with pytest.raises(RuntimeError):
        build_template_spec(template_path)


def test_validate_sections_flags_unexpected_divider(tmp_path: Path, template_path: Path) -> None:
    document = _write(
        tmp_path / "service.md",
        TEMPLATE_CONTENT.replace("**References:** Template", "**References:** Template **|**")
    )

    specs = build_template_spec(template_path)
    issues = validate_sections(document, specs, document.read_text(encoding="utf-8").splitlines())

    assert any("must not end" in issue for issue in issues)


def test_validate_sections_flags_trailing_space_star(tmp_path: Path, template_path: Path) -> None:
    document = _write(
        tmp_path / "service.md",
        TEMPLATE_CONTENT.replace("**References:** Template", "**References:** Template *")
    )

    specs = build_template_spec(template_path)
    issues = validate_sections(document, specs, document.read_text(encoding="utf-8").splitlines())

    assert any("must not end with ' *'" in issue for issue in issues)


def test_validate_sections_table_errors() -> None:
    spec = SectionSpec(
        numbering=(1,),
        level=2,
        title="1) Section",
        preamble_order=("Purpose",),
        preamble_requires_marker={"Purpose": True},
        tables=(
            TableSpec(
                header=("Col",),
                rows=(TableRowSpec(first_cell="foo", optional=False),),
            ),
        ),
        yaml_schemas=(),
        required_markers=(),
    )

    no_table_lines = ["## 1) Section", "**Purpose:** Demo **|**"]
    issues = cs.validate_sections(Path("doc.md"), [spec], no_table_lines)
    assert any("missing table" in issue for issue in issues)

    header_only_lines = [
        "## 1) Section",
        "**Purpose:** Demo **|**",
        "| Col |",
        "| --- |",
    ]
    issues = cs.validate_sections(Path("doc.md"), [spec], header_only_lines)
    assert any("must contain at least one data row" in issue for issue in issues)

    wrong_row_lines = [
        "## 1) Section",
        "**Purpose:** Demo **|**",
        "| Col |",
        "| --- |",
        "| other |",
    ]
    issues = cs.validate_sections(Path("doc.md"), [spec], wrong_row_lines)
    assert any("missing row 'foo'" in issue for issue in issues)


def test_validate_sections_requires_yaml_block(tmp_path: Path, template_path: Path) -> None:
    specs = build_template_spec(template_path)
    document = _write(tmp_path / "service.md", _strip_yaml_block(TEMPLATE_CONTENT))

    errors = validate_sections(document, specs, document.read_text(encoding="utf-8").splitlines())

    assert any("missing required YAML block" in error for error in errors)


def test_validate_sections_yaml_schema_enforced(tmp_path: Path, template_path: Path) -> None:
    specs = build_template_spec(template_path)
    document = _write(
        tmp_path / "service.md",
        _edit_yaml_block(
            TEMPLATE_CONTENT,
            lambda block: [line for line in block if not line.strip().startswith("client_action:")],
        ),
    )

    errors = validate_sections(document, specs, document.read_text(encoding="utf-8").splitlines())

    assert any("client_action" in error for error in errors)


def test_validate_sections_accepts_optional_metrics(tmp_path: Path, template_path: Path) -> None:
    specs = build_template_spec(template_path)
    document = _write(
        tmp_path / "service.md",
        _edit_yaml_block(
            TEMPLATE_CONTENT,
            lambda block: [line for line in block if not line.strip().startswith("related_metrics:")],
        ),
    )

    errors = validate_sections(document, specs, document.read_text(encoding="utf-8").splitlines())

    assert errors == []


def test_validate_sections_skips_unrelated_yaml_blocks(tmp_path: Path, template_path: Path) -> None:
    specs = build_template_spec(template_path)
    extra_block = """### 3.3 API Error Codes (binding)\n\n```yaml\napiVersion: v1\n```\n\n"""
    document = _write(
        tmp_path / "service.md",
        TEMPLATE_CONTENT.replace("### 3.3 API Error Codes (binding)\n\n", extra_block),
    )

    errors = validate_sections(document, specs, document.read_text(encoding="utf-8").splitlines())

    assert errors == []


def test_validate_sections_heading_with_anchor() -> None:
    spec = SectionSpec(
        numbering=(1,),
        level=2,
        title="1) Heading",
        preamble_order=("Purpose",),
        preamble_requires_marker={"Purpose": False},
        tables=(),
        yaml_schemas=(),
        required_markers=(),
    )
    lines = ["## 1) Heading {#anchor}", "**Purpose:** Demo"]

    issues = cs.validate_sections(Path("doc.md"), [spec], lines)

    assert issues == []


def test_main_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    services = tmp_path / "docs" / "src" / "services"
    services.mkdir(parents=True)
    template = services / "_template.md"
    template.write_text(TEMPLATE_CONTENT, encoding="utf-8")
    doc = _write_service_doc(services / "service.md")

    monkeypatch.setattr(cs, "parse_args", lambda: argparse.Namespace(paths=[doc], template=None, frontmatter=False))

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

    monkeypatch.setattr(cs, "parse_args", lambda: argparse.Namespace(paths=[services], template=None, frontmatter=False))

    rc = cs_main()

    captured = capsys.readouterr()
    assert rc == 1
    assert "missing or invalid YAML front matter" in captured.out


def test_main_frontmatter_only_skips_section_validation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    doc = _write(
        tmp_path / "service.md",
        """---
title: Sample
subtitle: Example
authors:
  - Alice
version: 1.0
status: draft
classification: Confidential
last_updated: 2025-01-01
updated_by: Alice
owners:
  - Team
reviewers:
  - Reviewer
approvers:
  - Approver
approved_by: 
approved_date: 
---

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Alice |
| Version | 1.0 |
| Status | draft |
| Classification | Confidential |
| Last updated | 2025-01-01 |
| Updated by | Alice |
| Owners | Team |
| Reviewers | Reviewer |
| Approvers | Approver |
| Approved by |  |
| Approved date |  |
<!-- END AUTO-GENERATED: document-controls -->
""",
    )

    monkeypatch.setattr(cs, "parse_args", lambda: argparse.Namespace(paths=[doc], template=None, frontmatter=True))

    rc = cs_main()

    captured = capsys.readouterr()
    assert rc == 0
    assert "synced front matter and document controls" in captured.out


def test_main_skips_disabled_template(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    services = tmp_path / "docs" / "src" / "services"
    services.mkdir(parents=True)
    template = services / "_template.md"
    template.write_text("<!-- template:disabled -->", encoding="utf-8")
    doc = _write_service_doc(services / "service.md")

    monkeypatch.setattr(
        cs,
        "parse_args",
        lambda: argparse.Namespace(paths=[doc], template=None, frontmatter=False),
    )

    rc = cs_main()

    captured = capsys.readouterr()
    assert rc == 0
    assert "marked as disabled" in captured.err


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
**References:** Doc
## 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc
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
**References:** Doc
### 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc
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
**References:** Doc
## 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc
## 3) Extras
Body text.
### 3.3 API Error Codes (binding)
| Code | Scenario | Client guidance |
| --- | --- | --- |
| `FOO` | Demo | Do a thing |

```yaml
error_codes:
  - code: FOO
    http_status: 400
    audit_required: false
    description: Demo
    client_action: Do a thing
```
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
**References:** Doc
## 2) Responsibilities (informative)
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc
## 3) Extras
Body text.
### 3.3 API Error Codes (binding)
| Code | Scenario | Client guidance |
| --- | --- | --- |
| `FOO` | Demo | Do a thing |

```yaml
error_codes:
  - code: FOO
    http_status: 400
    audit_required: false
    description: Demo
    client_action: Do a thing
```
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
**References:** Doc
## 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc
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
**References:** Doc
## 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc
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
**References:** Doc
## 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc
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
**References:** Doc
## 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc
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
**Extra:** Doc
## 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc
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
**References:** Doc
## 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc
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
**References:** Doc
## 2) Responsibilities
**Purpose:** Doc **|**
**Contract:** Doc **|**
**State:** Doc **|**
**Failures & handling:** Doc **|**
**Observability:** Doc **|**
**Breadcrumbs:** Doc **|**
**References:** Doc
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
        "title: Sample",
        "subtitle: Example",
        "author:",
        "  - Alice",
        "version: 1.0",
        "status: draft",
        "classification: Confidential",
        "last_updated: 2025-10-30",
        "updated_by: Alice",
        "owners:",
        "  - Team",
        "reviewers:",
        "  - Reviewer",
        "approvers:",
        "  - Approver",
        "extra_meta: Extra data",
        "approved_by: ",
        "approved_date: ",
        "---",
        "## Document controls",
        "<!-- BEGIN AUTO-GENERATED: document-controls -->",
        "| Field | Value |",
        "| ----- | ----- |",
        "| Authors | Alice |",
        "| Version | 1.0 |",
        "| Status | draft |",
        "| Classification | Confidential |",
        "| Last updated | 2025-10-30 |",
        "| Updated by | Alice |",
        "| Owners | Team |",
        "| Reviewers | Reviewer |",
        "| Approvers | Approver |",
        "| Approved by |  |",
        "| Approved date |  |",
        "| Extra Meta | Extra data |",
        "<!-- END AUTO-GENERATED: document-controls -->",
    ]

    errors = check_document_controls(Path("service.md"), lines)

    assert errors == []


def test_document_controls_additional_field_missing_row_detected() -> None:
    lines = [
        "---",
        "title: Sample",
        "subtitle: Example",
        "author: Alice",
        "version: 1.0",
        "status: draft",
        "classification: Confidential",
        "last_updated: 2025-10-30",
        "updated_by: Alice",
        "owners: Team",
        "reviewers: Reviewer",
        "approvers: Approver",
        "extra_meta: Extra data",
        "approved_by: ",
        "approved_date: ",
        "---",
        "## Document controls",
        "<!-- BEGIN AUTO-GENERATED: document-controls -->",
        "| Field | Value |",
        "| ----- | ----- |",
        "| Authors | Alice |",
        "| Version | 1.0 |",
        "| Status | draft |",
        "| Classification | Confidential |",
        "| Last updated | 2025-10-30 |",
        "| Updated by | Alice |",
        "| Owners | Team |",
        "| Reviewers | Reviewer |",
        "| Approvers | Approver |",
        "| Approved by |  |",
        "| Approved date |  |",
        "<!-- END AUTO-GENERATED: document-controls -->",
    ]

    errors = check_document_controls(Path("service.md"), lines)

    assert any("Extra Meta" in err for err in errors)


def test_document_controls_unexpected_field_detected() -> None:
    lines = [
        "---",
        "title: Sample",
        "subtitle: Example",
        "author: Alice",
        "version: 1.0",
        "status: draft",
        "classification: Confidential",
        "last_updated: 2025-10-30",
        "updated_by: Alice",
        "owners: Team",
        "reviewers: Reviewer",
        "approvers: Approver",
        "approved_by: ",
        "approved_date: ",
        "---",
        "## Document controls",
        "<!-- BEGIN AUTO-GENERATED: document-controls -->",
        "| Field | Value |",
        "| ----- | ----- |",
        "| Authors | Alice |",
        "| Version | 1.0 |",
        "| Status | draft |",
        "| Classification | Confidential |",
        "| Last updated | 2025-10-30 |",
        "| Updated by | Alice |",
        "| Owners | Team |",
        "| Reviewers | Reviewer |",
        "| Approvers | Approver |",
        "| Approved by |  |",
        "| Approved date |  |",
        "| Custom Field | 123 |",
        "<!-- END AUTO-GENERATED: document-controls -->",
    ]

    errors = check_document_controls(Path("service.md"), lines)

    assert any("unexpected field 'Custom Field'" in err for err in errors)


def test_document_controls_missing_field_detected() -> None:
    lines = [
        "---",
        "title: Sample",
        "subtitle: Example",
        "author: Author Name",
        "version: 1.0",
        "status: draft",
        "classification: Confidential",
        "last_updated: 2025-01-01",
        "updated_by: Alice",
        "owners:",
        "  - Owner Team",
        "reviewers:",
        "  - Reviewer",
        "approvers:",
        "  - Approver",
        "approved_by: ",
        "approved_date: ",
        "---",
        "",
        "## Document controls",
        "",
        "<!-- BEGIN AUTO-GENERATED: document-controls -->",
        "| Field | Value |",
        "| ----- | ----- |",
        "| Authors | |",
        "| Version | 1.0 |",
        "| Status | draft |",
        "| Classification | Confidential |",
        "| Last updated | 2025-01-01 |",
        "| Updated by | Alice |",
        "| Owners | Owner Team |",
        "| Reviewers | Reviewer |",
        "| Approvers | Approver |",
        "| Approved by | |",
        "| Approved date | |",
        "<!-- END AUTO-GENERATED: document-controls -->",
    ]

    errors = check_document_controls(Path("service.md"), lines)

    assert any("Authors" in err for err in errors)


def test_document_controls_mismatch_detected() -> None:
    lines = [
        "---",
        "title: Sample",
        "subtitle: Example",
        "author: Author Name",
        "version: 1.0",
        "status: draft",
        "classification: Confidential",
        "last_updated: 2025-01-01",
        "updated_by: Alice",
        "owners:",
        "  - Owner Team",
        "reviewers:",
        "  - Reviewer",
        "approvers:",
        "  - Approver",
        "approved_by: ",
        "approved_date: ",
        "---",
        "## Document controls",
        "<!-- BEGIN AUTO-GENERATED: document-controls -->",
        "| Field | Value |",
        "| ----- | ----- |",
        "| Authors | Someone Else |",
        "| Version | 1.0 |",
        "| Status | draft |",
        "| Classification | Confidential |",
        "| Last updated | 2025-01-01 |",
        "| Updated by | Alice |",
        "| Owners | Owner Team |",
        "| Reviewers | Reviewer |",
        "| Approvers | Approver |",
        "| Approved by | |",
        "| Approved date | |",
        "<!-- END AUTO-GENERATED: document-controls -->",
    ]

    errors = check_document_controls(Path("service.md"), lines)

    assert any("Authors" in err for err in errors)


def test_document_controls_optional_fields_blank() -> None:
    lines = [
        "---",
        "title: Sample",
        "subtitle: Example",
        "author: Author Name",
        "version: 1.0",
        "status: draft",
        "classification: Confidential",
        "last_updated: 2025-01-01",
        "updated_by: Alice",
        "owners:",
        "  - Owner Team",
        "reviewers:",
        "  - Reviewer",
        "approvers:",
        "  - Approver",
        "approved_by: ",
        "approved_date: ",
        "---",
        "## Document controls",
        "<!-- BEGIN AUTO-GENERATED: document-controls -->",
        "| Field | Value |",
        "| ----- | ----- |",
        "| Authors | Author Name |",
        "| Version | 1.0 |",
        "| Status | draft |",
        "| Classification | Confidential |",
        "| Last updated | 2025-01-01 |",
        "| Updated by | Alice |",
        "| Owners | Owner Team |",
        "| Reviewers | Reviewer |",
        "| Approvers | Approver |",
        "| Approved by | |",
        "| Approved date | |",
        "<!-- END AUTO-GENERATED: document-controls -->",
    ]

    errors = check_document_controls(Path("service.md"), lines)

    assert errors == []


def test_document_controls_missing_updated_by_field_detected() -> None:
    lines = [
        "---",
        "title: Sample",
        "subtitle: Example",
        "author: Alice",
        "version: 1.0",
        "status: draft",
        "classification: Confidential",
        "last_updated: 2025-01-01",
        "updated_by: Alice",
        "owners: Team",
        "reviewers: Reviewer",
        "approvers: Approver",
        "approved_by: ",
        "approved_date: ",
        "---",
        "## Document controls",
        "<!-- BEGIN AUTO-GENERATED: document-controls -->",
        "| Field | Value |",
        "| ----- | ----- |",
        "| Authors | Alice |",
        "| Version | 1.0 |",
        "| Status | draft |",
        "| Classification | Confidential |",
        "| Last updated | 2025-01-01 |",
        "| Owners | Team |",
        "| Reviewers | Reviewer |",
        "| Approvers | Approver |",
        "| Approved by | |",
        "| Approved date | |",
        "<!-- END AUTO-GENERATED: document-controls -->",
    ]

    errors = check_document_controls(Path("service.md"), lines)

    assert any("Updated by" in err for err in errors)


def test_document_controls_duplicate_field_detected() -> None:
    lines = [
        "---",
        "title: Sample",
        "subtitle: Example",
        "author: Alice",
        "version: 1.0",
        "status: draft",
        "classification: Confidential",
        "last_updated: 2025-01-01",
        "updated_by: Alice",
        "owners: Team",
        "reviewers: Reviewer",
        "approvers: Approver",
        "approved_by: ",
        "approved_date: ",
        "---",
        "## Document controls",
        "<!-- BEGIN AUTO-GENERATED: document-controls -->",
        "| Field | Value |",
        "| ----- | ----- |",
        "| Authors | Alice |",
        "| Version | 1.0 |",
        "| Status | draft |",
        "| Classification | Confidential |",
        "| Last updated | 2025-01-01 |",
        "| Updated by | Alice |",
        "| Owners | Team |",
        "| Owners | Duplicate |",
        "| Reviewers | Reviewer |",
        "| Approvers | Approver |",
        "<!-- END AUTO-GENERATED: document-controls -->",
        "| Approved by | |",
        "| Approved date | |",
    ]

    errors = check_document_controls(Path("service.md"), lines)

    assert any("duplicate fields" in err for err in errors)


def test_ensure_template_requirements_missing_key(tmp_path: Path) -> None:
    template = tmp_path / "_template.md"
    template.write_text(
        """---
title: Missing
subtitle: Example
author: Person
version: 0.1
status: draft
classification: Internal
last_updated: 2025-01-01
owners: []
reviewers: []
approvers: []
approved_by: 
approved_date: 
---

## Document Controls

| Field | Value |
| --- | --- |
| Authors | Person |
| Version | 0.1 |
| Status | draft |
| Classification | Internal |
| Last updated | 2025-01-01 |
| Owners |  |
| Reviewers |  |
| Approvers |  |
| Approved by |  |
| Approved date |  |
""",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError):
        ensure_template_requirements(template)

