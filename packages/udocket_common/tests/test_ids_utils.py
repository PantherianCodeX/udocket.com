from __future__ import annotations

# pyright: strict

from uuid import NAMESPACE_DNS, UUID, uuid5

import pytest

from packages.udocket_common import ids


def test_uuid5_from_content_deterministic() -> None:
    value_one = ids.uuid5_from_content("timeline", "42", "hello")
    value_two = ids.uuid5_from_content("timeline", "42", "hello")
    assert value_one == value_two


def test_uuid5_from_content_strips_whitespace_and_flattens_lists() -> None:
    derived = ids.uuid5_from_content([" timeline ", "foo "], (" bar", None))
    manual = ids.uuid5_from_content("timeline", "foo", "bar", "")
    assert derived == manual


def test_uuid5_from_content_supports_custom_namespace() -> None:
    result = ids.uuid5_from_content("a", namespace=NAMESPACE_DNS)
    assert result == uuid5(NAMESPACE_DNS, "a")


def test_uuid5_from_content_handles_bytes() -> None:
    value = ids.uuid5_from_content(b"alpha", bytearray(b"beta"))
    assert isinstance(value, UUID)
    assert value == ids.uuid5_from_content("alpha", "beta")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("abc", "abc"),
        ("  spaced  ", "spaced"),
        (b"bytes", "bytes"),
        (bytearray(b"array "), "array"),
        (UUID("12345678-1234-5678-1234-567812345678"), "12345678-1234-5678-1234-567812345678"),
        (None, None),
        ("   ", None),
    ],
)
def test_normalize_id_variants(raw: ids.UUIDInput, expected: str | None) -> None:
    assert ids.normalize_id(raw) == expected
