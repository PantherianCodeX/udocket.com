from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from scripts.docs import build_runbook_catalog as brc


def _setup_tmp_docs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    docs_root = tmp_path / "docs" / "src"
    services = docs_root / "services"
    services.mkdir(parents=True)
    apps = docs_root / "apps"
    apps.mkdir()
    output = docs_root / "ops" / "runbooks.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(brc, "SRC_DIR", docs_root)
    monkeypatch.setattr(brc, "OUTPUT_FILE", output)
    return services, output


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
