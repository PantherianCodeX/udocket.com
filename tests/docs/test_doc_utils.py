from __future__ import annotations

from pathlib import Path

import pytest

from scripts.docs import doc_utils as du


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


def test_parse_front_matter_without_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(du, "yaml", None)

    parsed = du.parse_front_matter(["---", "title: Example", "---"])

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


def test_stringify_dict_without_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(du, "yaml", None)

    result = du.stringify({"key": "value"})

    assert result == "{'key': 'value'}"


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
