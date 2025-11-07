# pyright: strict

"""Helpers for generating deterministic identifiers."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, MutableMapping, Sequence
from typing import Union, cast
from uuid import NAMESPACE_URL, UUID, uuid5

UUIDInput = Union[str, int, float, bytes, bytearray, UUID, None]


def _coerce_part(value: object) -> str:
    """Normalize a UUID component to a trimmed string."""

    if value is None:
        return ""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="ignore").strip()
        except Exception:
            return ""
    if isinstance(value, bytearray):
        return _coerce_part(bytes(value))
    text = str(value)
    return text.strip()


def _iter_normalized_parts(parts: Iterable[object]) -> Iterator[str]:
    """Yield normalized string parts from nested iterables."""

    for part in parts:
        if isinstance(part, Sequence) and not isinstance(part, (str, bytes, bytearray)):
            seq_part = cast(Sequence[object], part)
            for nested in seq_part:
                yield _coerce_part(nested)
        else:
            yield _coerce_part(part)


def uuid5_from_content(
    *parts: object,
    namespace: UUID = NAMESPACE_URL,
    separator: str = "|",
) -> UUID:
    """Generate a deterministic UUID5 from the provided content parts."""

    normalized = separator.join(_iter_normalized_parts(parts))
    return uuid5(namespace, normalized)


def normalize_id(value: UUIDInput) -> str | None:
    """Return a normalized string ID or None when empty."""

    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        try:
            decoded = value.decode("utf-8")
        except Exception:
            return None
        text = decoded.strip()
        return text or None
    if isinstance(value, bytearray):
        return normalize_id(bytes(value))
    text = str(value).strip()
    if not text:
        return None
    return text


def ensure_deterministic_uuids(
    items: Iterable[MutableMapping[str, object]],
    *,
    namespace: str,
    signature_fields: Sequence[str],
    id_field: str | None = "id",
    uuid_field: str = "uuid",
) -> None:
    """Mutate each mapping so it carries a stable UUID derived from the signature fields.

    Existing UUID/ID values are preserved when present. Otherwise a UUID5 is generated using the
    supplied namespace and normalized field content and assigned to ``uuid_field`` and, when set,
    ``id_field``.
    """

    for mapping in items:
        existing_uuid = normalize_id(cast(UUIDInput, mapping.get(uuid_field)))
        if not existing_uuid and id_field:
            existing_uuid = normalize_id(cast(UUIDInput, mapping.get(id_field)))
        if existing_uuid:
            mapping[uuid_field] = existing_uuid
            if id_field:
                current_id = normalize_id(cast(UUIDInput, mapping.get(id_field)))
                if not current_id:
                    mapping[id_field] = existing_uuid
            continue

        signature = tuple(
            str(mapping.get(field, "") or "").strip().lower() for field in signature_fields
        )
        derived = uuid5_from_content(namespace, *signature)
        uuid_value = str(derived)
        mapping[uuid_field] = uuid_value
        if id_field:
            mapping[id_field] = uuid_value


__all__ = ["uuid5_from_content", "normalize_id", "ensure_deterministic_uuids"]
