# pyright: strict

"""Shared helpers for normalising JSON input/output across the project."""

from __future__ import annotations

import json
from pathlib import Path
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, TypeAlias, cast

JSONPrimitive: TypeAlias = int | float | bool | str | None
JSONValue: TypeAlias = JSONPrimitive | dict[str, "JSONValue"] | list["JSONValue"]
JSONObject: TypeAlias = dict[str, JSONValue]
JSONArray: TypeAlias = list[JSONValue]


def is_json_scalar(value: object) -> bool:
    """Return ``True`` when ``value`` is already JSON-serialisable as a scalar."""
    return isinstance(value, (str, int, float, bool)) or value is None


def coerce_json_value(value: object) -> JSONValue:
    """Coerce ``value`` into a JSON-compatible structure."""
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
    """Return a JSON object derived from ``value`` or ``default`` when absent."""
    if isinstance(value, Mapping):
        mapping_value = cast(Mapping[object, object], value)
        return {str(key): coerce_json_value(item) for key, item in mapping_value.items()}
    return {} if default is None else dict(default)


def merge_json_objects(*objects: object) -> JSONObject:
    """Merge mapping-like objects into a single JSON object."""

    merged: JSONObject = {}
    for candidate in objects:
        if not isinstance(candidate, Mapping):
            continue
        mapping_value = cast(Mapping[object, object], candidate)
        for key, value in mapping_value.items():
            merged[str(key)] = coerce_json_value(value)
    return merged


def json_object_to_dict(payload: JSONObject) -> dict[str, Any]:
    """Convert a ``JSONObject`` into a plain ``dict`` with ``Any`` values."""

    return {key: cast(Any, value) for key, value in payload.items()}


def ensure_json_object(value: object, *, context: str | None = None) -> JSONObject:
    """Return a JSON object or raise a ``ValueError`` with optional context."""
    if not isinstance(value, Mapping):
        if context:
            raise ValueError(f"Expected mapping for {context}, received {type(value)!r}")
        raise ValueError(f"Expected mapping, received {type(value)!r}")
    mapping_value = cast(Mapping[object, object], value)
    return {str(key): coerce_json_value(item) for key, item in mapping_value.items()}


def coerce_json_array(value: object) -> JSONArray:
    """Return a JSON array derived from ``value`` (falling back to ``[]``)."""
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence_value = cast(Sequence[object], value)
        return [coerce_json_value(item) for item in sequence_value]
    return []


def coerce_object_list(value: object) -> list[JSONObject]:
    """Return list of JSON objects extracted from ``value`` when iterable."""
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
    """Return a mapping of strings coerced from ``value`` when possible."""

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
    """Coerce ``value`` into a trimmed string when possible."""
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
    """Coerce ``value`` into a boolean when possible."""
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
    """Read ``path`` and return a coerced ``JSONValue`` or ``None`` on failure."""
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
    """Read ``path`` and return a JSON object, falling back to ``default``."""
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
    """Serialise ``payload`` to ``path`` ensuring parent directories exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized: JSONObject = {
        str(key): coerce_json_value(value) for key, value in payload.items()
    }
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=indent), encoding="utf-8")


def parse_json_value(data: str) -> JSONValue | None:
    """Parse ``data`` into a ``JSONValue`` or return ``None`` when invalid."""

    try:
        raw = json.loads(data)
    except json.JSONDecodeError:
        return None
    return coerce_json_value(raw)


def parse_json_value_strict(data: str, *, context: str | None = None) -> JSONValue:
    """Parse ``data`` and raise ``ValueError`` when the payload is invalid."""

    try:
        raw = json.loads(data)
    except json.JSONDecodeError as exc:  # pragma: no cover - pass-through
        label = context or "JSON payload"
        raise ValueError(f"Invalid {label}: {exc}") from exc
    return coerce_json_value(raw)


def parse_json_object(data: str, *, context: str | None = None) -> JSONObject:
    """Parse ``data`` and return a JSON object, raising ``ValueError`` when invalid."""

    value = parse_json_value_strict(data, context=context)
    if not isinstance(value, dict):
        label = context or "JSON payload"
        raise ValueError(f"Expected JSON object for {label}")
    return value


def load_json_object(path: Path, *, context: str | None = None) -> JSONObject:
    """Read ``path`` and return a JSON object, raising when parsing fails."""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - pass-through
        label = context or str(path)
        raise ValueError(f"Unable to read JSON file {label}: {exc}") from exc
    label = context or str(path)
    return parse_json_object(text, context=label)


def load_json_value(path: Path, *, context: str | None = None) -> JSONValue:
    """Read ``path`` and return a JSON value, raising ``ValueError`` when invalid."""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - pass-through
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
    """Serialise ``value`` to ``path`` ensuring parent directories exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, (dict, list)):
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=indent),
            encoding="utf-8",
        )
    else:
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


__all__ = [
    "JSONPrimitive",
    "JSONValue",
    "JSONObject",
    "JSONArray",
    "is_json_scalar",
    "coerce_json_value",
    "coerce_json_object",
    "merge_json_objects",
    "ensure_json_object",
    "coerce_json_array",
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
]
