# pyright: strict

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import TypeAlias, cast

JSONPrimitive: TypeAlias = int | float | bool | str | None
JSONValue: TypeAlias = JSONPrimitive | dict[str, "JSONValue"] | list["JSONValue"]
JSONObject: TypeAlias = dict[str, JSONValue]
JSONArray: TypeAlias = list[JSONValue]


def is_json_scalar(value: object) -> bool:
    return isinstance(value, (str, int, float, bool)) or value is None


def coerce_json_value(value: object) -> JSONValue:
    if is_json_scalar(value):
        return cast(JSONPrimitive, value)
    if isinstance(value, Mapping):
        mapping_value = cast(Mapping[object, object], value)
        return {str(key): coerce_json_value(item) for key, item in mapping_value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence_value = cast(Sequence[object], value)
        return [coerce_json_value(item) for item in sequence_value]
    return str(value)


def coerce_json_object(value: object, *, default: JSONObject | None = None) -> JSONObject:
    if isinstance(value, Mapping):
        mapping_value = cast(Mapping[object, object], value)
        return {str(key): coerce_json_value(item) for key, item in mapping_value.items()}
    return {} if default is None else dict(default)


def ensure_json_object(value: object, *, context: str | None = None) -> JSONObject:
    if not isinstance(value, Mapping):
        if context:
            raise ValueError(f"Expected mapping for {context}, received {type(value)!r}")
        raise ValueError(f"Expected mapping, received {type(value)!r}")
    mapping_value = cast(Mapping[object, object], value)
    return {str(key): coerce_json_value(item) for key, item in mapping_value.items()}


def coerce_json_array(value: object) -> JSONArray:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence_value = cast(Sequence[object], value)
        return [coerce_json_value(item) for item in sequence_value]
    return []


def coerce_object_list(value: object) -> list[JSONObject]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence_value = cast(Sequence[object], value)
        result: list[JSONObject] = []
        for item in sequence_value:
            if isinstance(item, Mapping):
                mapping_item = cast(Mapping[object, object], item)
                result.append(coerce_json_object(mapping_item))
        return result
    return []


def coerce_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    text = str(value).strip()
    return text or None


def coerce_str_list(
    value: object,
    *,
    unique: bool = True,
    drop_empty: bool = True,
    lower: bool = False,
) -> list[str]:
    if isinstance(value, str):
        items: list[str] = [value]
    elif isinstance(value, Iterable):
        iterable = cast(Iterable[object], value)
        items = [str(item) for item in iterable if item is not None]
    else:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        candidate = item.strip()
        if lower:
            candidate = candidate.lower()
        if drop_empty and not candidate:
            continue
        if unique:
            if candidate in seen:
                continue
            seen.add(candidate)
        normalized.append(candidate)
    return normalized


def coerce_int(
    value: object,
    *,
    default: int | None = None,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int | None:
    if isinstance(value, bool):
        candidate = int(value)
    elif isinstance(value, int):
        candidate = value
    elif isinstance(value, float):
        candidate = int(value)
    elif isinstance(value, str):
        try:
            candidate = int(value.strip())
        except ValueError:
            candidate = default
    else:
        candidate = default
    if candidate is None:
        return None
    if minimum is not None and candidate < minimum:
        candidate = minimum
    if maximum is not None and candidate > maximum:
        candidate = maximum
    return candidate


def coerce_float(
    value: object,
    *,
    default: float | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float | None:
    candidate: float | None
    if isinstance(value, bool):
        candidate = float(value)
    elif isinstance(value, (int, float)):
        candidate = float(value)
    elif isinstance(value, str):
        try:
            candidate = float(value.strip())
        except ValueError:
            candidate = default
    else:
        candidate = default
    if candidate is None:
        return None
    if minimum is not None and candidate < minimum:
        candidate = minimum
    if maximum is not None and candidate > maximum:
        candidate = maximum
    return candidate


def coerce_bool(value: object, *, default: bool | None = None) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y", "on"}:
            return True
        if lowered in {"false", "0", "no", "n", "off"}:
            return False
    return default


__all__ = [
    "JSONPrimitive",
    "JSONValue",
    "JSONObject",
    "JSONArray",
    "is_json_scalar",
    "coerce_json_value",
    "coerce_json_object",
    "ensure_json_object",
    "coerce_json_array",
    "coerce_object_list",
    "coerce_str",
    "coerce_str_list",
    "coerce_int",
    "coerce_float",
    "coerce_bool",
]
