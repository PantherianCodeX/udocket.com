from __future__ import annotations

# pyright: strict

"""Pure helpers for encoding dataclasses into JSON-safe structures."""

from dataclasses import fields, is_dataclass
from typing import Any, Mapping, Sequence, cast


def to_jsonable(value: Any) -> Any:
    """Recursively convert dataclasses and enums into JSON-friendly types."""

    if is_dataclass(value):
        return {
            field.name: to_jsonable(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        mapping = cast(Mapping[Any, Any], value)
        return {str(key): to_jsonable(val) for key, val in mapping.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence = cast(Sequence[Any], value)
        return [to_jsonable(item) for item in sequence]
    if hasattr(value, "value"):
        return getattr(value, "value")
    return value


__all__ = ["to_jsonable"]
