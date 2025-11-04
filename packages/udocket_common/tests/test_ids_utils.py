from __future__ import annotations

from collections.abc import MutableMapping

# pyright: strict
from typing import cast
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


def test_uuid5_from_content_accepts_uuid_objects() -> None:
    namespace_uuid = UUID("12345678-1234-5678-1234-567812345678")
    derived = ids.uuid5_from_content(namespace_uuid)
    assert derived == ids.uuid5_from_content(str(namespace_uuid))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("abc", "abc"),
        ("  spaced  ", "spaced"),
        (b"bytes", "bytes"),
        (bytearray(b"array "), "array"),
        (
            UUID("12345678-1234-5678-1234-567812345678"),
            "12345678-1234-5678-1234-567812345678",
        ),
        (None, None),
        ("   ", None),
    ],
)
def test_normalize_id_variants(raw: ids.UUIDInput, expected: str | None) -> None:
    assert ids.normalize_id(raw) == expected


def test_ensure_deterministic_uuids_preserves_existing() -> None:
    items: list[MutableMapping[str, object]] = [
        cast(MutableMapping[str, object], {"uuid": "existing", "id": "", "title": "Same"})
    ]
    ids.ensure_deterministic_uuids(items, namespace="outline.issues", signature_fields=("title",))
    assert items[0]["uuid"] == "existing"
    assert items[0]["id"] == "existing"


def test_ensure_deterministic_uuids_assigns_when_missing() -> None:
    items: list[MutableMapping[str, object]] = [
        cast(MutableMapping[str, object], {"title": "Claim", "description": "Damages"})
    ]
    ids.ensure_deterministic_uuids(
        items, namespace="outline.claims", signature_fields=("title", "description")
    )
    derived = ids.normalize_id(cast(ids.UUIDInput, items[0]["uuid"]))
    assert derived is not None
    assert items[0]["id"] == derived
    # deterministic across invocations
    items2: list[MutableMapping[str, object]] = [
        cast(MutableMapping[str, object], {"title": "Claim", "description": "Damages"})
    ]
    ids.ensure_deterministic_uuids(
        items2, namespace="outline.claims", signature_fields=("title", "description")
    )
    assert items2[0]["uuid"] == derived


def test_ensure_deterministic_uuids_without_id_field() -> None:
    items: list[MutableMapping[str, object]] = [
        cast(MutableMapping[str, object], {"name": "Jordan Counsel", "for": "Applicant"})
    ]
    ids.ensure_deterministic_uuids(
        items,
        namespace="outline.parties.counsel",
        signature_fields=("name", "for"),
        id_field=None,
    )
    assert ids.normalize_id(cast(ids.UUIDInput, items[0]["uuid"])) is not None
    assert "id" not in items[0]
