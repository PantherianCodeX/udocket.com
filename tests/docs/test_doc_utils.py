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
