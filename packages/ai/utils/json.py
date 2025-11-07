# pyright: strict

"""Pure helpers for encoding dataclasses into JSON-safe structures."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from typing import Protocol, cast, runtime_checkable

JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | dict[str, "JSONValue"] | list["JSONValue"]


@runtime_checkable
class HasValue(Protocol):
    """Protocol for enums/objects that expose a .value attribute."""

    value: JSONScalar


def to_jsonable(value: object) -> JSONValue:
    """Recursively convert dataclasses and enums into JSON-friendly types."""

    if is_dataclass(value):
        return {field.name: to_jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        mapping_value = cast("Mapping[object, object]", value)
        return {str(key): to_jsonable(val) for key, val in mapping_value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence_value = cast("Sequence[object]", value)
        return [to_jsonable(item) for item in sequence_value]
    if isinstance(value, HasValue):
        return to_jsonable(value.value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    msg = f"Unsupported value {value!r} of type {type(value)!r} for JSON encoding"
    raise TypeError(msg)


__all__ = ["to_jsonable"]
