from __future__ import annotations

from pathlib import Path

import pytest

from doc_tools.common import doc_utils as du


def test_read_markdown_lines(tmp_path: Path) -> None:
    target = tmp_path / "sample.md"
    target.write_text("a\nb\n", encoding="utf-8")

    lines = du.read_markdown_lines(target)

    assert lines == ["a", "b"]


def test_parse_front_matter_success(monkeypatch: pytest.MonkeyPatch) -> None:
    lines = [
        "---",
        "title: Example",
        "authors:",
        "  - Alice",
        "  - Bob",
        "---",
        "Body",
    ]

    parsed = du.parse_front_matter(lines)

    assert parsed["title"] == "Example"
    assert parsed["authors"] == ["Alice", "Bob"]


def test_parse_front_matter_missing_separator() -> None:
    parsed = du.parse_front_matter(["title: Example"])

    assert parsed == {}
def test_parse_front_matter_invalid_yaml_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(Exception):
        du.parse_front_matter(["---", "title: [unbalanced", "---"])


def test_parse_front_matter_returns_empty_for_non_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    class StubYaml:
        @staticmethod
        def safe_load(_: str) -> object:
            return ["not-a-dict"]

    monkeypatch.setattr(du, "yaml", StubYaml())

    parsed = du.parse_front_matter(["---", "title: Alpha", "---"])

    assert parsed == {}


@pytest.mark.parametrize(
    ("value", "slug"),
    [
        ("Hello World", "hello-world"),
        ("Multi__dash--Test", "multi-dash-test"),
        ("  Caps & Spaces  ", "caps-spaces"),
    ],
)
def test_slugify(value: str, slug: str) -> None:
    assert du.slugify(value) == slug


def test_replace_marked_section_success() -> None:
    original = "A\n<!-- START -->\nold\n<!-- END -->\nB"
    updated = du.replace_marked_section(original, "<!-- START -->", "<!-- END -->", "new content")
    assert "new content" in updated
    assert "old" not in updated


def test_replace_marked_section_missing_marker() -> None:
    with pytest.raises(RuntimeError):
        du.replace_marked_section("body", "<!-- A -->", "<!-- B -->", "x")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (" hello ", "hello"),
        (b"bytes", "bytes"),
        (["a", "  ", "b"], "a; b"),
        ({"k": "v"}, "k: v"),
        (123, "123"),
    ],
)
def test_stringify_various_types(value: object, expected: str) -> None:
    assert du.stringify(value) == expected


@pytest.mark.parametrize(
    ("title", "fallback", "expected"),
    [
        ("uDocket — Alpha Service Specification", "Alpha", "Alpha Service"),
        ("uDocket — Technical Design Document", "TDD", "Technical Design Document"),
        ("", "Fallback", "Fallback"),
    ],
)
def test_derive_doc_label(title: str, fallback: str, expected: str) -> None:
    assert du.derive_doc_label(title, fallback=fallback) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("My Field", "my_field"),
        ("Already_Snake", "already_snake"),
        ("HTTP Header", "http_header"),
    ],
)
def test_normalize_key(raw: str, expected: str) -> None:
    assert du.normalize_key(raw) == expected


@pytest.mark.parametrize(
    ("raw", "variants"),
    [
        ("Owners", ("owners", "owner")),
    ("status", ("status", "statu")),
        ("\tValue\t", ("value", "values")),
    ],
)
def test_key_variants(raw: str, variants: tuple[str, ...]) -> None:
    assert du.key_variants(raw) == variants


@pytest.mark.parametrize(
    ("raw", "label"),
    [
        ("audit_event", "Audit Event"),
        ("RB-RES", "Rb Res"),
        ("last_updated", "Last Updated"),
        ("  __multi--value__  ", "Multi Value"),
    ],
)
def test_format_label(raw: str, label: str) -> None:
    assert du.format_label(raw) == label


def test_split_table_row() -> None:
    assert du.split_table_row("| a | b | ") == ["a", "b"]
    assert du.split_table_row("not a row") == []


def test_is_table_separator() -> None:
    assert du.is_table_separator("| --- | --- |") is True
    assert du.is_table_separator("| a | b |") is False
    assert du.is_table_separator("|    | --- |") is False


def test_normalize_table_cell() -> None:
    assert du.normalize_table_cell(" ` value ` ") == "value"
    assert du.normalize_table_cell("plain") == "plain"


def test_iter_markdown_tables(tmp_path: Path) -> None:
    lines = [
        "Intro",
        "| Col | Value |",
        "| --- | --- |",
        "| alpha | bravo |",
        "",
        "| Name | Notes |",
        "| --- | --- |",
        "| [optional] Foo | Bar |",
    ]

    tables = list(du.iter_markdown_tables(lines, allow_optional_tags=True))

    assert len(tables) == 2
    _, first_rows = tables[0]
    assert first_rows[0].strip() == "| Col | Value |"
    _, second_rows = tables[1]
    assert any("[optional] Foo" in row for row in second_rows)


def test_iter_markdown_tables_skips_code_fences() -> None:
    lines = [
        "```",
        "| Col | Value |",
        "| --- | --- |",
        "| data | value |",
        "```",
    ]

    tables = list(du.iter_markdown_tables(lines))

    assert tables == []


def test_iter_markdown_tables_requires_separator() -> None:
    lines = ["| Col | Value |"]

    tables = list(du.iter_markdown_tables(lines))

    assert tables == []


def test_auto_generated_comment_with_command_sequence() -> None:
    comment = du.auto_generated_comment(refresh_command=["python", "-m", "tool.build"])
    assert comment == "<!-- AUTO-GENERATED: Run `python -m tool.build` to refresh. -->"


def test_auto_generated_comment_with_note() -> None:
    comment = du.auto_generated_comment(note="Managed elsewhere.")
    assert comment == "<!-- AUTO-GENERATED: Managed elsewhere. -->"


def test_auto_generated_comment_defaults_to_note() -> None:
    comment = du.auto_generated_comment()
    assert comment == "<!-- AUTO-GENERATED: Managed automatically; do not edit manually. -->"


def test_auto_generated_header_returns_comment_and_blank_line() -> None:
    header = du.auto_generated_header(refresh_command="python -m tool.run")
    assert header == ["<!-- AUTO-GENERATED: Run `python -m tool.run` to refresh. -->", ""]


def test_iter_markdown_tables_rejects_non_separator_row() -> None:
    lines = [
        "| Col | Value |",
        "| value | entry |",
    ]

    tables = list(du.iter_markdown_tables(lines))

    assert tables == []


def test_iter_markdown_tables_skips_extra_separators() -> None:
    lines = [
        "| Col | Value |",
        "| --- | --- |",
        "| --- | --- |",
        "| item | data |",
    ]

    tables = list(du.iter_markdown_tables(lines))

    assert len(tables) == 1
    _, rows = tables[0]
    assert "| item | data |" in rows


def test_iter_yaml_blocks_detects_blocks() -> None:
    lines = [
        "Intro",
        "```yaml",
        "key: value",
        "```",
    ]

    blocks = list(du.iter_yaml_blocks(lines))

    assert len(blocks) == 1
    start, block_lines = blocks[0]
    assert start == 1
    assert block_lines == ["key: value"]


def test_is_optional_yaml_value_handles_variants() -> None:
    assert du.is_optional_yaml_value("[optional]") is True
    assert du.is_optional_yaml_value("optional") is True
    assert du.is_optional_yaml_value("required") is False


def test_build_yaml_schema_marks_optional_sequence() -> None:
    schema = du.build_yaml_schema(["[optional]"])

    assert schema.kind == "sequence"
    assert schema.optional is True


def test_validate_yaml_schema_allows_missing_optional_sequence() -> None:
    schema = du.build_yaml_schema({"metrics": ["[optional]"]})
    errors: list[str] = []

    du.validate_yaml_schema(schema, {}, [], errors)

    assert errors == []


def test_validate_yaml_schema_rejects_wrong_type() -> None:
    schema = du.build_yaml_schema({"metrics": ["value"]})
    errors: list[str] = []

    du.validate_yaml_schema(schema, {"metrics": "not-a-list"}, [], errors)

    assert any("expected list" in error for error in errors)


def test_begin_end_auto_generated_marker() -> None:
    begin = du.begin_auto_generated_marker("example-tag")
    end = du.end_auto_generated_marker("example-tag")
    assert begin == "<!-- BEGIN AUTO-GENERATED: example-tag -->"
    assert end == "<!-- END AUTO-GENERATED: example-tag -->"


def test_replace_auto_generated_section() -> None:
    original = "\n".join(
        [
            "A",
            du.begin_auto_generated_marker("sample"),
            "old",
            du.end_auto_generated_marker("sample"),
            "B",
        ]
    )
    updated = du.replace_auto_generated_section(original, "sample", "new content")
    assert "new content" in updated
    assert "old" not in updated


def test_write_or_check(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "file.txt"
    # Write when file missing
    result_write = du.write_or_check(path, "hello\n", check=False)
    assert result_write is True
    assert path.read_text(encoding="utf-8") == "hello\n"

    # Check success
    assert du.write_or_check(path, "hello\n", check=True) is True

    # Check failure with message
    assert (
        du.write_or_check(path, "bye\n", check=True, stale_message="stale message")
        is False
    )
    captured = capsys.readouterr()
    assert "stale message" in captured.err


def test_unescape_markdown_removes_escapes() -> None:
    assert du.unescape_markdown(r"\| foo \* bar") == "| foo * bar"


def test_split_table_row_handles_backticks() -> None:
    row = r"| `a\|b` | value\|data |"
    cells = du.split_table_row(row)
    assert cells == ["`a\\|b`", "value\\|data"]


def test_build_document_control_map_include_additional() -> None:
    front = {
        "authors": ["Alice"],
        "owners": ["Ops"],
        "custom_field": "Custom value",
    }
    base = du.build_document_control_map(front, include_additional=False)
    assert "Custom Field" not in base

    extended = du.build_document_control_map(front, include_additional=True)
    assert extended["Custom Field"] == "Custom value"


def test_parse_markdown_table_returns_records() -> None:
    rows = [
        "| A | B |",
        "| --- | --- |",
        "| one | two |",
        "| three |",
        "| | |",
    ]

    records = du.parse_markdown_table(rows)

    assert records[0]["A"] == "one"
    assert records[1]["B"] == ""


def test_iter_yaml_blocks_multiple() -> None:
    lines = [
        "```yaml",
        "first: block",
        "```",
        "",
        "```yaml",
        "second: block",
        "```",
    ]

    blocks = list(du.iter_yaml_blocks(lines))

    assert len(blocks) == 2
    assert blocks[0][1] == ["first: block"]
    assert blocks[1][1] == ["second: block"]


def test_validate_yaml_schema_errors_and_sequences() -> None:
    schema = du.build_yaml_schema({"code": "value", "notes": ["[optional]"]})
    errors: list[str] = []

    du.validate_yaml_schema(schema, None, [], errors)
    du.validate_yaml_schema(schema, {"notes": ["entry1", "entry2"]}, [], errors)

    assert any("<root>: value missing" in err for err in errors)

    errors.clear()
    du.validate_yaml_schema(schema, {"code": "ok"}, [], errors)
    assert errors == []
