from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from doc_tools.build import slo_index as bsi


def _setup_docs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    docs_root = tmp_path / "docs"
    services_dir = docs_root / "services"
    services_dir.mkdir(parents=True)
    apps_dir = docs_root / "apps"
    apps_dir.mkdir()

    appendix = docs_root / "overview" / "tdd" / "appendices" / "slo_index.md"
    appendix.parent.mkdir(parents=True, exist_ok=True)
    appendix.write_text(
        "\n".join([
            "Intro",
            bsi.BEGIN_MARKER,
            "PLACEHOLDER",
            bsi.END_MARKER,
        ]),
        encoding="utf-8",
    )

    monkeypatch.setattr(bsi, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(bsi, "DOCS_DIR", docs_root)
    monkeypatch.setattr(bsi, "SERVICE_ROOTS", [Path("services"), Path("apps")])
    monkeypatch.setattr(bsi, "APPENDIX_FILE", appendix)
    monkeypatch.setattr(bsi, "APPENDIX_DIR", appendix.parent)
    return docs_root


def test_collects_slo_sections(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup_docs(tmp_path, monkeypatch)

    service_doc = docs_root / "services" / "alpha.md"
    service_doc.write_text(
        dedent(
            """
            ---
            title: Service — Alpha Spec
            ---

            ## 6) Observability

            ### 6.1 SLOs & Targets (binding)

            - **Example:** 99.9% availability.

            ### 6.2 Metrics
            More text.
            """
        ),
        encoding="utf-8",
    )

    apps_doc = docs_root / "apps" / "web.md"
    apps_doc.write_text(
        dedent(
            """
            ---
            title: App — Web Portal
            ---

            ## 6) Observability

            ### 6.1 SLOs & Targets
            - Portal uptime ≥99.9%.

            ## 7) Security
            ...
            """
        ),
        encoding="utf-8",
    )

    content = bsi.build_content()
    assert "Alpha Spec" in content
    assert "Portal" in content
    assert "99.9%" in content


def test_check_mode_detects_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    docs_root = _setup_docs(tmp_path, monkeypatch)
    (docs_root / "services" / "alpha.md").write_text(
        dedent(
            """
            ## 6) Observability

            ### 6.1 SLOs & Targets
            - Item
            """
        ),
        encoding="utf-8",
    )

    rc = bsi.main(["--check"])
    assert rc == 1
    assert "SLO index is stale" in capsys.readouterr().err


def test_main_writes_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup_docs(tmp_path, monkeypatch)
    (docs_root / "services" / "alpha.md").write_text(
        dedent(
            """
            ## 6) Observability

            ### 6.1 SLOs & Targets
            - Item
            """
        ),
        encoding="utf-8",
    )

    rc = bsi.main([])
    assert rc == 0
    updated = bsi.APPENDIX_FILE.read_text(encoding="utf-8")
    assert "Item" in updated
