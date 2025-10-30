from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from scripts.docs import build_api_error_index as baei


def _setup_docs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    docs_root = tmp_path / "docs" / "src"
    services_dir = docs_root / "services"
    services_dir.mkdir(parents=True)
    apps_dir = docs_root / "apps"
    apps_dir.mkdir()

    appendix = docs_root / "overview" / "tdd" / "appendices" / "api_error_codes.md"
    appendix.parent.mkdir(parents=True, exist_ok=True)
    appendix.write_text(
        "\n".join(
            [
                "Intro",
                "<!-- BEGIN AUTO-GENERATED API ERROR INDEX -->",
                "PLACEHOLDER",
                "<!-- END AUTO-GENERATED API ERROR INDEX -->",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(baei, "SRC_DIR", docs_root)
    monkeypatch.setattr(baei, "APPENDIX_FILE", appendix)
    monkeypatch.setattr(baei, "APPENDIX_DIR", appendix.parent)
    return docs_root


def test_collects_api_error_sections(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup_docs(tmp_path, monkeypatch)

    service_doc = docs_root / "services" / "alpha.md"
    service_doc.write_text(
        dedent(
            """
            ---
            title: Service — Alpha Spec
            ---

            ### 3.3 API error codes (binding)

            | Code | Scenario | Client guidance |
            | --- | --- | --- |
            | `EXAMPLE` | Demo scenario | Do something |
            ### Appendix
            """
        ).lstrip(),
        encoding="utf-8",
    )

    app_doc = docs_root / "apps" / "web.md"
    app_doc.write_text(
        dedent(
            """
            ---
            title: App — Web Portal
            ---

            ### 3.3 API error codes (binding)

            Some prose.

            | Code | Scenario | Client guidance |
            | --- | --- | --- |
            | `APP` | Portal issue | Refresh |
            """
        ).lstrip(),
        encoding="utf-8",
    )

    content = baei.build_content()
    assert "Alpha Spec" in content
    assert "Portal" in content
    assert "EXAMPLE" in content
    assert "APP" in content


def test_check_mode_detects_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    docs_root = _setup_docs(tmp_path, monkeypatch)
    (docs_root / "services" / "alpha.md").write_text(
        dedent(
            """
            ### 3.3 API error codes (binding)

            | Code | Scenario | Client guidance |
            | --- | --- | --- |
            | `X` | Y | Z |
            """
        ),
        encoding="utf-8",
    )

    rc = baei.main(["--check"])
    assert rc == 1
    assert "API error index is stale" in capsys.readouterr().err


def test_render_no_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup_docs(tmp_path, monkeypatch)
    content = baei.render([])

    assert "No API error code sections" in content


def test_render_entry_without_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup_docs(tmp_path, monkeypatch)
    doc_path = docs_root / "services" / "alpha.md"
    doc_path.write_text("ignored", encoding="utf-8")
    entry = baei.ApiSection(doc_path=doc_path, display_name="Alpha", content=[])

    rendered = baei.render([entry])

    assert "_No API error codes documented._" in rendered


def test_collect_entries_skips_templates_and_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup_docs(tmp_path, monkeypatch)
    (docs_root / "services" / "_template.md").write_text("content", encoding="utf-8")
    (docs_root / "services" / "empty.md").write_text("### Heading", encoding="utf-8")

    entries = baei.collect_entries()

    assert entries == []


def test_adjust_relative_links_rewrites_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup_docs(tmp_path, monkeypatch)
    doc = docs_root / "services" / "alpha.md"
    lines = ["See [Platform](../services/platform-runtime.md#33-api-error-codes) for catalog."]

    adjusted = baei.adjust_relative_links(lines, doc)

    assert "(../../../services/platform-runtime.md#33-api-error-codes)" in adjusted[0]


def test_extract_api_section_trims_padding(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup_docs(tmp_path, monkeypatch)
    doc = docs_root / "services" / "alpha.md"
    doc.write_text(
        dedent(
            """
            ### 3.3 API error codes (binding)

            line 1

            """
        ).lstrip(),
        encoding="utf-8",
    )

    section = baei.extract_api_section(doc)

    assert section == ["line 1"]


def test_main_writes_updated_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup_docs(tmp_path, monkeypatch)
    doc = docs_root / "services" / "alpha.md"
    doc.write_text(
        dedent(
            """
            ---
            title: Alpha
            ---

            ### 3.3 API error codes (binding)

            | Code | Scenario | Client guidance |
            | --- | --- | --- |
            | `CODE` | Scenario | Guidance |
            """
        ).lstrip(),
        encoding="utf-8",
    )

    rc = baei.main([])

    assert rc == 0
    generated = (docs_root / "overview" / "tdd" / "appendices" / "api_error_codes.md").read_text(encoding="utf-8")
    assert "CODE" in generated


def test_main_check_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup_docs(tmp_path, monkeypatch)
    doc = docs_root / "services" / "alpha.md"
    doc.write_text(
        dedent(
            """
            ### 3.3 API error codes (binding)

            | Code | Scenario | Client guidance |
            | --- | --- | --- |
            | `CODE` | Scenario | Guidance |
            """
        ).lstrip(),
        encoding="utf-8",
    )

    assert baei.main([]) == 0
    assert baei.main(["--check"]) == 0
