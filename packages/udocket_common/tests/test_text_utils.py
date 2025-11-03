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
