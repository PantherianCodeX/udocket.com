from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from doc_tools.check import templates as tmpl
from doc_tools.check.requirements import TemplateRequirements
from doc_tools.config.header_includes import HeaderIncludesConfig

VALID_TEMPLATE = dedent(
    """\
    ---
    title: Template Spec
    subtitle: Overview
    authors:
      - Template Author
    version: 1.0
    status: draft
    classification: Internal
    last_updated: 2024-01-01
    updated_by: Docs Team
    owners:
      - Platform
    reviewers:
      - QA
    approvers:
      - Legal
    approved_by:
    approved_date:
    ---

    ## Document Controls

    | Field | Value |
    | --- | --- |
    | Authors | Template Author |
    | Version | 1.0 |
    | Status | draft |
    | Classification | Internal |
    | Last updated | 2024-01-01 |
    | Updated by | Docs Team |
    | Owners | Platform |
    | Reviewers | QA |
    | Approvers | Legal |
    | Approved by |  |
    | Approved date |  |
    """
)


def _write_template(tmp_path: Path, content: str = VALID_TEMPLATE) -> Path:
    path = tmp_path / "_template.md"
    path.write_text(content, encoding="utf-8")
    return path


def test_check_template_passes_valid_file(tmp_path: Path) -> None:
    template = _write_template(tmp_path)

    errors = tmpl.check_template(template)

    assert errors == []


def test_check_template_missing_front_matter_key(tmp_path: Path) -> None:
    content = VALID_TEMPLATE.replace("classification: Internal\n", "")
    template = _write_template(tmp_path, content=content)

    errors = tmpl.check_template(template)

    assert any("classification" in error.lower() for error in errors)


def test_check_template_missing_document_controls_row(tmp_path: Path) -> None:
    content = VALID_TEMPLATE.replace("| Owners | Platform |\n", "")
    template = _write_template(tmp_path, content=content)

    errors = tmpl.check_template(template)

    assert any("Owners" in error for error in errors)


def test_check_template_detects_dynamic_placeholders(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    template = _write_template(tmp_path)
    fake_config = HeaderIncludesConfig(
        blocks=(
            "<header>{<title>}{<program_lead>}</header>",
        ),
        subtitle_lead="",
        front_matter_placeholders=frozenset({"title", "program_lead"}),
        builtin_placeholders=frozenset(),
    )
    monkeypatch.setattr(tmpl, "HEADER_INCLUDES_CONFIG", fake_config, raising=False)
    monkeypatch.setattr(
        tmpl,
        "TEMPLATE_REQUIREMENTS",
        TemplateRequirements(header_config=fake_config),
        raising=False,
    )

    errors = tmpl.check_template(template)

    assert any("program lead" in error.lower() for error in errors)


def test_builtins_do_not_require_front_matter(tmp_path: Path) -> None:
    template = _write_template(tmp_path)

    errors = tmpl.check_template(template)

    assert not any("page_number" in error or "page_count" in error for error in errors)
