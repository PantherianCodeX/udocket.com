from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from doc_tools.build import api_error_codes as generator


SUMMARY_TABLE = "| Code | Scenario | Client guidance |"
CATALOG_TABLE = "| Code | HTTP Status | Audit Required | Metrics |"


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).lstrip("\n"), encoding="utf-8")
    return path


def _setup_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    docs_root = tmp_path / "docs"
    appendix = _write(
        docs_root / "overview" / "tdd" / "appendices" / "api_error_codes.md",
        "\n".join(
            [
                "Intro",
                generator.APPENDIX_BEGIN,
                "PLACEHOLDER",
                generator.APPENDIX_END,
            ]
        ),
    )

    monkeypatch.setattr(generator, "DOCS_DIR", docs_root)
    roots = [Path("services"), Path("apps")]
    monkeypatch.setattr(generator, "DOC_ROOTS", [docs_root / root for root in roots])
    monkeypatch.setattr(generator, "APPENDIX_FILE", appendix)
    monkeypatch.setattr(generator, "APPENDIX_DIR", appendix.parent)
    return docs_root


def _service_docs(docs_root: Path) -> tuple[Path, Path]:
    doc = _write(
        docs_root / "services" / "alpha.md",
        f"""
        ---
        title: Service — Alpha Spec
        ---

        ## 1) Purpose
        Placeholder

        ### 3.3 API Error Codes (binding)

        Preamble text.

        {generator.SUMMARY_BEGIN}
        {generator.SUMMARY_END}

        {generator.CATALOG_BEGIN}
        {generator.CATALOG_END}
        """,
    )
    yaml_file = _write(
        doc.parent / doc.stem / "error_codes.yaml",
        """
        error_codes:
          - code: ALPHA_CONFLICT
            http_status: 409
            audit_required: false
            description: Concurrent update detected.
            client_action: Refresh state and retry with new Idempotency-Key.
            related_metrics:
              - alpha_api_error_total
          - code: ALPHA_POLICY_BLOCK
            http_status: 403
            audit_required: true
            description: Residency policy denied the action.
            client_action: Obtain waiver or adjust residency configuration.
        """,
    )
    return doc, yaml_file


def _app_docs(docs_root: Path) -> tuple[Path, Path]:
    doc = _write(
        docs_root / "apps" / "portal.md",
        f"""
        ---
        title: Portal — Web Application
        ---

        ### 3.3 API Error Codes (binding)

        Context paragraph.

        {generator.SUMMARY_BEGIN}
        {generator.SUMMARY_END}

        {generator.CATALOG_BEGIN}
        {generator.CATALOG_END}
        """,
    )
    yaml_file = _write(
        doc.parent / doc.stem / "error_codes.yaml",
        """
        error_codes:
          - code: PORTAL_RATE_LIMIT
            http_status: 429
            audit_required: false
            description: Too many login attempts.
            client_action: Honor Retry-After and surface throttling guidance.
        """,
    )
    return doc, yaml_file


def test_generator_populates_tables_and_appendix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup_workspace(tmp_path, monkeypatch)
    service_doc, _ = _service_docs(docs_root)
    app_doc, _ = _app_docs(docs_root)

    rc = generator._run([])
    assert rc == 0

    service_text = service_doc.read_text(encoding="utf-8")
    assert SUMMARY_TABLE in service_text
    assert "`ALPHA_CONFLICT`" in service_text
    assert CATALOG_TABLE in service_text
    assert "<!-- BEGIN AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->" in service_text
    assert "> Tables generated" not in service_text

    app_text = app_doc.read_text(encoding="utf-8")
    assert "`PORTAL_RATE_LIMIT`" in app_text
    assert "<!-- BEGIN AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->" in app_text

    appendix_text = generator.APPENDIX_FILE.read_text(encoding="utf-8")
    assert "ALPHA_CONFLICT" in appendix_text
    assert "Web Application" in appendix_text
    assert "#alpha-spec" in appendix_text
    assert "#web-application" in appendix_text


def test_check_mode_detects_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    docs_root = _setup_workspace(tmp_path, monkeypatch)
    service_doc, yaml_file = _service_docs(docs_root)
    _app_docs(docs_root)
    # initial render
    assert generator._run([]) == 0

    yaml_file.write_text(
        """
        error_codes:
          - code: ALPHA_CONFLICT
            http_status: 409
            audit_required: false
            description: Updated description.
            client_action: New guidance.
        """,
        encoding="utf-8",
    )

    rc = generator._run(["--check"])
    assert rc == 1
    assert "API error codes tables are stale" in capsys.readouterr().err

    # re-run to update
    assert generator._run([]) == 0
    text = service_doc.read_text(encoding="utf-8")
    assert "| `ALPHA_CONFLICT` | Updated description. | New guidance. |" in text


def test_missing_yaml_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup_workspace(tmp_path, monkeypatch)
    # create doc without yaml
    _write(
        docs_root / "services" / "alpha.md",
        """
        ---
        title: Service — Alpha Spec
        ---

        ### 3.3 API Error Codes (binding)

        <!-- BEGIN AUTO-GENERATED: api-error-codes:summary -->
        <!-- END AUTO-GENERATED: api-error-codes:summary -->

        <!-- BEGIN AUTO-GENERATED: api-error-codes:catalog -->
        <!-- END AUTO-GENERATED: api-error-codes:catalog -->
        """,
    )

    with pytest.raises(RuntimeError, match="expected error_codes.yaml"):
        generator.build_content(check=False)


def test_load_entries_validates_schema(tmp_path: Path) -> None:
    bad_root = tmp_path / "invalid"
    bad_root.write_text("- item", encoding="utf-8")
    with pytest.raises(RuntimeError, match="expected mapping"):
        generator._load_entries(bad_root)

    empty = tmp_path / "empty.yaml"
    empty.write_text("error_codes: []", encoding="utf-8")
    with pytest.raises(RuntimeError, match="non-empty list"):
        generator._load_entries(empty)

    missing_fields = tmp_path / "missing.yaml"
    missing_fields.write_text(
        """
        error_codes:
          - code: ALPHA
            http_status: 200
            audit_required: true
            client_action: Do it.
        """,
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="missing required field 'description'"):
        generator._load_entries(missing_fields)


def test_load_entries_validates_field_types(tmp_path: Path) -> None:
    invalid_status = tmp_path / "status.yaml"
    invalid_status.write_text(
        """
        error_codes:
          - code: BAD_STATUS
            http_status: not-a-number
            audit_required: true
            description: Example.
            client_action: Retry.
        """,
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="must be an integer"):
        generator._load_entries(invalid_status)

    out_of_range = tmp_path / "range.yaml"
    out_of_range.write_text(
        """
        error_codes:
          - code: RANGE
            http_status: 42
            audit_required: true
            description: Example.
            client_action: Retry.
        """,
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="between 100 and 599"):
        generator._load_entries(out_of_range)

    invalid_bool = tmp_path / "bool.yaml"
    invalid_bool.write_text(
        """
        error_codes:
          - code: BOOL
            http_status: 409
            audit_required: "sometimes"
            description: Example.
            client_action: Retry.
        """,
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="must be boolean"):
        generator._load_entries(invalid_bool)


def test_normalize_metrics_handles_variants() -> None:
    assert generator._normalize_metrics(None) == []
    assert generator._normalize_metrics("metric_total") == ["metric_total"]
    assert generator._normalize_metrics(["metric_a", " [optional] ", ""]) == ["metric_a"]
    with pytest.raises(RuntimeError, match="must be string or list"):
        generator._normalize_metrics(object())


def test_render_tables_cover_branches() -> None:
    empty_summary = generator._render_summary_table([])
    assert empty_summary == ["_No API error codes documented._"]
    empty_catalog = generator._render_catalog_table([])
    assert empty_catalog == ["_No API error codes documented._"]

    entry = generator.ErrorCodeEntry(
        code="ALPHA",
        scenario="Conflict occurred",
        client_action="Retry.",
        http_status="409",
        audit_required=True,
        metrics=["alpha_metric|count"],
        description="Concurrent update detected.",
    )
    lines = generator._render_summary_table([entry])
    assert "<br>_Concurrent update detected._" in lines[2]

    catalog = generator._render_catalog_table([entry])
    assert "alpha_metric\\|count" in "\n".join(catalog)


def test_replace_block_missing_marker() -> None:
    with pytest.raises(RuntimeError, match="Missing marker"):
        generator._replace_block("body", "<!-- START -->", "<!-- END -->", ["content"])


def test_cross_link_updates_existing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    appendix = tmp_path / "appendix.md"
    appendix.write_text("placeholder", encoding="utf-8")
    component = generator.Component(
        doc_path=tmp_path / "services" / "alpha.md",
        yaml_path=tmp_path / "services" / "alpha" / "error_codes.yaml",
        display_name="Alpha Service",
        section_anchor="3-3-alpha",
        index_anchor="alpha",
        entries=[],
    )
    component.doc_path.parent.mkdir(parents=True, exist_ok=True)
    component.yaml_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        generator.CROSS_LINK_PREFIX + "(../old.md#old-anchor)",
        generator.SUMMARY_BEGIN,
        generator.SUMMARY_END,
    ]
    monkeypatch.setattr(generator, "APPENDIX_FILE", appendix)

    generator._ensure_cross_link(lines, component)

    assert lines[0].startswith(generator.CROSS_LINK_PREFIX)
    assert lines[1] == ""


def test_heading_anchor_added_when_missing() -> None:
    lines = [
        "### 3.3 API Error Codes (binding)",
        generator.SUMMARY_BEGIN,
        generator.SUMMARY_END,
    ]
    component = generator.Component(
        doc_path=Path("docs/platform/example.md"),
        yaml_path=Path("docs/platform/example/error_codes.yaml"),
        display_name="Example",
        section_anchor="3-3-example",
        index_anchor="example",
        entries=[],
    )

    generator._ensure_heading_anchor(lines, component)

    assert "{#3-3-example}" in lines[0]


def test_remove_legacy_notes() -> None:
    lines = [
        generator.NOTE_PREFIX + "doc`",
        "",
        "content",
    ]
    generator._remove_legacy_notes(lines)
    assert lines == ["content"]


def test_collect_components_requires_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup_workspace(tmp_path, monkeypatch)
    doc = _write(
        docs_root / "services" / "missing.md",
        """
        ### 3.3 API Error Codes (binding)
        """,
    )

    with pytest.raises(RuntimeError, match="expected error_codes.yaml"):
        generator._collect_components()


def test_find_section_anchor_without_inline_anchor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup_workspace(tmp_path, monkeypatch)
    doc = _write(
        docs_root / "services" / "beta.md",
        """
        ### 3.3 API Error Codes (binding)
        """,
    )
    yaml_file = doc.parent / doc.stem / "error_codes.yaml"
    yaml_file.parent.mkdir(parents=True, exist_ok=True)
    yaml_file.write_text(
        """
        error_codes:
          - code: BETA
            http_status: 400
            audit_required: false
            description: Example.
            client_action: Fix input.
        """,
        encoding="utf-8",
    )

    anchor = generator._find_section_anchor(doc)

    assert anchor.startswith("3-3")


def test_render_appendix_outputs_links(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_root = _setup_workspace(tmp_path, monkeypatch)
    doc, yaml_file = _service_docs(docs_root)
    generator._run([])
    components = generator._collect_components()

    appendix = generator._render_appendix(components)

    assert "ALPHA_CONFLICT" in appendix
    assert "(../../../services/alpha.md#3-3-api-error-codes-binding)" in appendix
