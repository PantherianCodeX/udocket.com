from __future__ import annotations

# pyright: strict

"""Utility helpers for working with JSON-compatible structures."""

import json
from pathlib import Path
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Callable, TypeAlias, TypeVar, cast, overload

JSONPrimitive: TypeAlias = int | float | bool | str | None
JSONValue: TypeAlias = JSONPrimitive | dict[str, "JSONValue"] | list["JSONValue"]
JSONObject: TypeAlias = dict[str, JSONValue]
JSONArray: TypeAlias = list[JSONValue]

KeyT = TypeVar("KeyT")
ValueT = TypeVar("ValueT")
ResultT = TypeVar("ResultT")


def is_json_scalar(value: object) -> bool:
    """Return True when the value is a JSON scalar (str/int/float/bool/None)."""

    return isinstance(value, (str, int, float, bool)) or value is None


def coerce_json_value(value: object) -> JSONValue:
    """Coerce an arbitrary object into a JSON-compatible value."""

    if is_json_scalar(value):
        return cast(JSONPrimitive, value)
    if isinstance(value, Mapping):
        mapping_value = cast(Mapping[object, object], value)
        return {str(key): coerce_json_value(item) for key, item in mapping_value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence_value = cast(Sequence[object], value)
        return [coerce_json_value(item) for item in sequence_value]
    return str(value)


def json_payload(**items: object) -> JSONObject:
    """Return a JSON object with values coerced to JSON-compatible types."""

    return {key: coerce_json_value(value) for key, value in items.items()}


def coerce_json_object(value: object, *, default: JSONObject | None = None) -> JSONObject:
    """Return a JSON object (dict[str, JSONValue]) from the provided mapping."""

    if isinstance(value, Mapping):
        mapping_value = cast(Mapping[object, object], value)
        return {str(key): coerce_json_value(item) for key, item in mapping_value.items()}
    return {} if default is None else dict(default)


def merge_json_objects(*objects: object) -> JSONObject:
    """Merge any JSON-mappable objects into a single dictionary."""

    merged: JSONObject = {}
    for candidate in objects:
        if not isinstance(candidate, Mapping):
            continue
        mapping_value = cast(Mapping[object, object], candidate)
        for key, value in mapping_value.items():
            merged[str(key)] = coerce_json_value(value)
    return merged


def json_object_to_dict(payload: JSONObject) -> dict[str, Any]:
    """Convert a JSONObject into a plain dictionary with Any values."""

    return {key: cast(Any, value) for key, value in payload.items()}


@overload
def normalize_mapping(mapping: Mapping[KeyT, ValueT]) -> dict[str, ValueT]:
    ...


@overload
def normalize_mapping(
    mapping: Mapping[KeyT, ValueT],
    *,
    transform: Callable[[ValueT], ResultT],
) -> dict[str, ResultT]:
    ...


def normalize_mapping(
    mapping: Mapping[KeyT, ValueT],
    *,
    transform: Callable[[ValueT], ResultT] | None = None,
) -> dict[str, ValueT] | dict[str, ResultT]:
    """Return a new dict with stringified keys and optional value transformation."""

    if transform is None:
        base: dict[str, ValueT] = {}
        for key, value in mapping.items():
            base[str(key)] = value
        return base
    converted: dict[str, ResultT] = {}
    for key, value in mapping.items():
        converted[str(key)] = transform(value)
    return converted


def normalize_mapping_optional(
    value: object,
    *,
    transform: Callable[[Any], Any] | None = None,
) -> dict[str, Any]:
    """Normalize mappings while gracefully handling non-mapping inputs."""

    if not isinstance(value, Mapping):
        return {}
    mapping_value = cast(Mapping[str, Any], value)
    if transform is None:
        normalized = normalize_mapping(mapping_value)
    else:
        normalized = normalize_mapping(mapping_value, transform=transform)
    return dict(normalized)


def coerce_object_dict(
    value: object,
    *,
    key_transform: Callable[[str], str] | None = None,
    drop_empty_keys: bool = False,
    drop_none_values: bool = False,
) -> dict[str, object]:
    """Coerce a mapping into a dict[str, object] applying optional key/value filtering."""

    base = normalize_mapping_optional(value)

    transform: Callable[[str], str] = key_transform or (lambda text: text)
    result: dict[str, object] = {}
    for raw_key, raw_value in base.items():
        key = transform(raw_key)
        if drop_empty_keys and not key:
            continue
        if drop_none_values and raw_value is None:
            continue
        result[key] = raw_value
    return result


def normalize_json_object(
    value: object,
    *,
    strip_keys: bool = True,
    drop_empty_keys: bool = False,
    drop_nullish_values: bool = False,
) -> JSONObject:
    """Normalize keys/values of a JSON object while optionally dropping empty entries."""

    payload = coerce_json_object(value)
    result: JSONObject = {}
    for key, raw in payload.items():
        normalized_key = key.strip() if strip_keys else key
        if drop_empty_keys and not normalized_key:
            continue
        if drop_nullish_values:
            if raw is None:
                continue
            if isinstance(raw, (str, bytes)) and raw == "":
                continue
            if isinstance(raw, (list, dict)) and not raw:
                continue
        result[normalized_key] = raw
    return result


def ensure_json_object(value: object, *, context: str | None = None) -> JSONObject:
    """Validate that a value is a mapping and coerce it into a JSONObject."""

    if not isinstance(value, Mapping):
        if context:
            raise ValueError(f"Expected mapping for {context}, received {type(value)!r}")
        raise ValueError(f"Expected mapping, received {type(value)!r}")
    mapping_value = cast(Mapping[object, object], value)
    return {str(key): coerce_json_value(item) for key, item in mapping_value.items()}


def coerce_json_array(value: object) -> JSONArray:
    """Coerce an iterable into a JSON array."""

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence_value = cast(Sequence[object], value)
        return [coerce_json_value(item) for item in sequence_value]
    return []


def coerce_object_list(value: object) -> list[JSONObject]:
    """Return a list of JSONObjects from a sequence of mappings."""

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence_value = cast(Sequence[object], value)
        result: list[JSONObject] = []
        for item in sequence_value:
            if isinstance(item, Mapping):
                mapping_item = cast(Mapping[object, object], item)
                result.append(coerce_json_object(mapping_item))
        return result
    return []


def coerce_str_dict(
    value: object,
    *,
    drop_empty: bool = True,
    value_drop_empty: bool = True,
    lower_keys: bool = False,
) -> dict[str, str]:
    """Coerce a mapping into dict[str, str] with filtering options."""

    if not isinstance(value, Mapping):
        return {}
    mapping_value = cast(Mapping[object, object], value)
    result: dict[str, str] = {}
    for key, raw_value in mapping_value.items():
        key_str = str(key).strip()
        if lower_keys:
            key_str = key_str.lower()
        if drop_empty and not key_str:
            continue
        value_str = coerce_str(raw_value)
        if value_drop_empty and not value_str:
            continue
        if value_str is None:
            continue
        result[key_str] = value_str
    return result


def coerce_str(value: object) -> str | None:
    """Convert a value to a trimmed string or None if empty."""

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
    """Coerce an iterable into a list of normalized strings."""

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
    """Coerce a value to an int, enforcing optional bounds."""

    candidate: int | None
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
    result = candidate
    if minimum is not None and result < minimum:
        result = minimum
    if maximum is not None and result > maximum:
        result = maximum
    return result


def coerce_float(
    value: object,
    *,
    default: float | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float | None:
    """Coerce a value to a float, enforcing optional bounds."""

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
    """Coerce a value into a boolean using common string representations."""

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


def read_json_value(path: Path) -> JSONValue | None:
    """Read a JSON file and return the value, or None on failure."""

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError:
        return None
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return None
    return coerce_json_value(raw)


def read_json_object(path: Path, *, default: JSONObject | None = None) -> JSONObject:
    """Read a JSON file and return a dict, falling back to the provided default."""

    value = read_json_value(path)
    if isinstance(value, dict):
        return value
    return {} if default is None else dict(default)


def write_json_object(
    path: Path,
    payload: Mapping[str, object],
    *,
    indent: int = 2,
) -> None:
    """Write a mapping to disk as JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    normalized: JSONObject = {
        str(key): coerce_json_value(value) for key, value in payload.items()
    }
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=indent), encoding="utf-8")


def parse_json_value(data: str) -> JSONValue | None:
    """Parse JSON text into a JSONValue, returning None on error."""

    try:
        raw = json.loads(data)
    except json.JSONDecodeError:
        return None
    return coerce_json_value(raw)


def parse_json_value_strict(data: str, *, context: str | None = None) -> JSONValue:
    """Parse JSON text into a JSONValue, raising ValueError on error."""

    try:
        raw = json.loads(data)
    except json.JSONDecodeError as exc:
        label = context or "JSON payload"
        raise ValueError(f"Invalid {label}: {exc}") from exc
    return coerce_json_value(raw)


def parse_json_object(data: str, *, context: str | None = None) -> JSONObject:
    """Parse JSON text into a JSONObject, enforcing object shape."""

    value = parse_json_value_strict(data, context=context)
    if not isinstance(value, dict):
        label = context or "JSON payload"
        raise ValueError(f"Expected JSON object for {label}")
    return value


def load_json_object(path: Path, *, context: str | None = None) -> JSONObject:
    """Load a JSON object from disk, raising ValueError on failure."""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        label = context or str(path)
        raise ValueError(f"Unable to read JSON file {label}: {exc}") from exc
    label = context or str(path)
    return parse_json_object(text, context=label)


def load_json_value(path: Path, *, context: str | None = None) -> JSONValue:
    """Load arbitrary JSON data from disk, raising ValueError on failure."""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        label = context or str(path)
        raise ValueError(f"Unable to read JSON file {label}: {exc}") from exc
    label = context or str(path)
    return parse_json_value_strict(text, context=label)


def write_json_value(
    path: Path,
    value: JSONValue,
    *,
    indent: int = 2,
) -> None:
    """Write a JSON-compatible value to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, (dict, list)):
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=indent),
            encoding="utf-8",
        )
    else:
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def stringify_json(value: object, *, indent: int | None = None, sort_keys: bool = False) -> str:
    """Return a JSON string for any object after coercion."""

    coerced = coerce_json_value(value)
    return json.dumps(coerced, ensure_ascii=False, indent=indent, sort_keys=sort_keys)


def stringify_pretty(value: object, *, sort_keys: bool = True) -> str:
    """Return a pretty-printed JSON string."""

    return stringify_json(value, indent=2, sort_keys=sort_keys)


__all__ = [
    "JSONPrimitive",
    "JSONValue",
    "JSONObject",
    "JSONArray",
    "is_json_scalar",
    "coerce_json_value",
    "json_payload",
    "coerce_json_object",
    "merge_json_objects",
    "ensure_json_object",
    "coerce_json_array",
    "normalize_mapping",
    "normalize_mapping_optional",
    "coerce_object_list",
    "coerce_str_dict",
    "coerce_str",
    "coerce_str_list",
    "coerce_int",
    "coerce_float",
    "coerce_bool",
    "read_json_value",
    "read_json_object",
    "write_json_object",
    "json_object_to_dict",
    "parse_json_value",
    "parse_json_value_strict",
    "parse_json_object",
    "load_json_value",
    "load_json_object",
    "write_json_value",
    "stringify_json",
    "stringify_pretty",
]
