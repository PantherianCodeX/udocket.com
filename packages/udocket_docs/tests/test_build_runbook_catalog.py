from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from doc_tools import doc_utils as du
from doc_tools.build import runbook_catalog as brc


def _setup_tmp_docs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    docs_root = tmp_path / "docs"
    area_root = docs_root / "platform"
    area_root.mkdir(parents=True, exist_ok=True)
    output = docs_root / "ops" / "runbooks.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(brc, "DOCS_DIR", docs_root)
    monkeypatch.setattr(brc, "OUTPUT_FILE", output)
    monkeypatch.setattr(brc.paths, "SERVICE_ROOTS", [area_root])
    return area_root, output


def test_build_catalog_transforms_sections(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    services, _ = _setup_tmp_docs(tmp_path, monkeypatch)
    doc_path = services / "guardian.md"
    doc_path.write_text(
        dedent(
            """\
            ---
            title: "Service — Guardian Specification"
            ---

            ## 8) Operations

            ### Incident Runbook
            Steps line 1.

            #### RB-GRD-INCIDENT — Contain Guardian Outage
            Step A.
            Step B.

            - RB-GRD-INCIDENT ensures Guardian outages fail closed.
            """
        ),
        encoding="utf-8",
    )

    catalog_lines, headings = brc.build_catalog()

    assert catalog_lines[0].startswith("## Guardian — Incident Runbook")
    assert '<a id="rb-grd-incident"></a>' in "\n".join(catalog_lines)
    assert headings and headings[0].text.startswith("Guardian — Incident Runbook")


def test_render_handles_empty_catalog() -> None:
    result = brc.render([])

    assert result.startswith("---")
    assert brc.BEGIN_MARKER in result
    assert brc.END_MARKER in result
    comment = du.auto_generated_comment(refresh_command="python -m docs.tools.build.runbook_catalog")
    assert comment in result
    assert "_No runbook sections detected._" in result


def test_main_check_detects_stale_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _, output = _setup_tmp_docs(tmp_path, monkeypatch)
    output.write_text("old content\n", encoding="utf-8")

    monkeypatch.setattr(brc, "build_catalog", lambda: (["New Content"], []))

    rc = brc.main(["--check"])

    captured = capsys.readouterr()
    assert rc == 1
    assert "Runbook catalog is stale" in captured.err


def test_main_writes_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, output = _setup_tmp_docs(tmp_path, monkeypatch)
    monkeypatch.setattr(brc, "build_catalog", lambda: (["Line A", "Line B"], []))

    rc = brc.main([])

    assert rc == 0
    content = output.read_text(encoding="utf-8")
    assert "Line A" in content
    assert content.startswith("---")


def test_build_catalog_inserts_anchors_for_lists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    services, _ = _setup_tmp_docs(tmp_path, monkeypatch)
    doc_path = services / "lpe.md"
    doc_path.write_text(
        dedent(
            """
            ## 8) Operations

            ### Runbook Summary

            - RB-LPE-COMPILER handles compiler regressions.
            """
        ),
        encoding="utf-8",
    )

    catalog_lines, _ = brc.build_catalog()

    assert any('<a id="rb-lpe-compiler"></a>' in line for line in catalog_lines)
    assert any(line.startswith("- <a id=\"rb-lpe-compiler\"") for line in catalog_lines)


def test_build_catalog_skips_table_anchor_injection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    services, _ = _setup_tmp_docs(tmp_path, monkeypatch)
    doc_path = services / "runbook-table.md"
    doc_path.write_text(
        dedent(
            """
            ## 8) Operations

            ### Runbook Index

            | Code | Notes |
            | --- | --- |
            | RB-RES-BLOCK | Residency block remediation |
            """
        ),
        encoding="utf-8",
    )

    catalog_lines, _ = brc.build_catalog()

    row = next(line for line in catalog_lines if "RB-RES-BLOCK" in line)
    assert "<a id=" not in row


def test_iter_source_files_skips_templates_and_missing_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = tmp_path / "docs"
    platform_root = docs_root / "platform"
    platform_root.mkdir(parents=True, exist_ok=True)
    portal_doc = platform_root / "portal.md"
    portal_doc.write_text("### Runbook", encoding="utf-8")
    (platform_root / "_template.md").write_text("ignored", encoding="utf-8")
    monkeypatch.setattr(brc, "DOCS_DIR", docs_root)
    monkeypatch.setattr(brc.paths, "SERVICE_ROOTS", [platform_root])

    sources = list(brc.iter_source_files())

    assert sources == [portal_doc]


def test_transform_section_requires_h2_level() -> None:
    section = ["# Runbook Overview"]

    with pytest.raises(ValueError):
        brc.transform_section(section, "Alpha", Path("alpha.md"))


def test_transform_section_plain_text_anchor_injection() -> None:
    section = [
        "## Runbook Overview",
        "Refer to RB-ALPHA-123 for detailed steps.",
    ]

    transformed, _ = brc.transform_section(section, "Alpha", Path("alpha.md"))

    assert '<a id="rb-alpha-123"></a>' in transformed


def test_transform_section_adds_spacing_before_anchor() -> None:
    section = [
        "### Runbook Summary",
        "Immediate response steps.",
        "#### RB-ALPHA-456 — Contain Outage",
        "Final notes.",
    ]

    transformed, headings = brc.transform_section(section, "Alpha", Path("alpha.md"))

    anchor_index = transformed.index('<a id="rb-alpha-456"></a>')
    assert transformed[anchor_index - 1] == ""
    assert any(h.text.startswith("Alpha — RB-ALPHA-456") for h in headings)


def test_build_catalog_adds_spacing_between_sections(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    services, _ = _setup_tmp_docs(tmp_path, monkeypatch)
    doc_path = services / "multi.md"
    doc_path.write_text(
        dedent(
            """
            ## 8) Operations

            ### First Runbook
            Step 1

            ### Second Runbook
            Step 2
            """
        ),
        encoding="utf-8",
    )

    catalog_lines, _ = brc.build_catalog()

    joined = "\n".join(catalog_lines)
    assert "First Runbook" in joined and "Second Runbook" in joined
    assert "\n\n##" in joined


def test_build_catalog_skips_documents_without_sections(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    services, _ = _setup_tmp_docs(tmp_path, monkeypatch)
    (services / "no-runbook.md").write_text("# Heading\n\nBody", encoding="utf-8")

    catalog_lines, headings = brc.build_catalog()

    assert catalog_lines == []
    assert headings == []


def test_main_check_missing_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _, output = _setup_tmp_docs(tmp_path, monkeypatch)
    if output.exists():
        output.unlink()
    monkeypatch.setattr(brc, "build_catalog", lambda: ([], []))

    rc = brc.main(["--check"])

    captured = capsys.readouterr()
    assert rc == 1
    assert "Runbook catalog is missing" in captured.err


def test_main_check_up_to_date(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, output = _setup_tmp_docs(tmp_path, monkeypatch)
    monkeypatch.setattr(brc, "build_catalog", lambda: (["Content"], []))

    assert brc.main([]) == 0
    assert brc.main(["--check"]) == 0
