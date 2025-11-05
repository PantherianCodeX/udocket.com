from __future__ import annotations

import pytest

from packages.udocket_common import text


@pytest.mark.parametrize(
    "source,expected",
    [
        ("Hello World", "hello-world"),
        ("Already-slug", "already-slug"),
        ("Trim   Spaces", "trim-spaces"),
    ],
)
def test_slugify_default(source: str, expected: str) -> None:
    assert text.slugify(source) == expected


def test_slugify_custom_separator() -> None:
    assert text.slugify("Make Group", separator=".") == "make.group"


def test_unique_title_first_available() -> None:
    assert text.unique_title("Transcript", []) == "Transcript-1"


def test_unique_title_when_exists_without_suffix() -> None:
    existing = ["Transcript"]
    assert text.unique_title("Transcript", existing) == "Transcript-1"


def test_unique_title_takes_highest_suffix() -> None:
    existing = ["Transcript-1", "Transcript(3)", "Transcript(4)"]
    assert text.unique_title("Transcript", existing) == "Transcript-5"


def test_unique_title_preserves_other_titles() -> None:
    existing = ["Analyze", "Transcript-2"]
    assert text.unique_title("Transcript", existing) == "Transcript-3"


def test_slugify_without_separator() -> None:
    assert text.slugify("Hello  World!", separator="") == "helloworld"


def test_unique_title_ignores_non_numeric_suffix() -> None:
    existing = ["TitleAlpha", "Title-2"]
    assert text.unique_title("Title", existing) == "Title-3"


def test_prompt_lines_trims_trailing_whitespace() -> None:
    assert text.prompt_lines("Line 1  ", "Line 2\n") == "Line 1\nLine 2"


def test_prompt_paragraphs_inserts_blank_line() -> None:
    result = text.prompt_paragraphs("First line", "Second block")
    assert result == "First line\n\nSecond block"
