from __future__ import annotations

# pyright: strict

"""Helpers for generating deterministic identifiers."""

from collections.abc import Iterable, Sequence
from typing import Iterator, Union, cast
from uuid import UUID, NAMESPACE_URL, uuid5


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


__all__ = ["uuid5_from_content", "normalize_id"]
