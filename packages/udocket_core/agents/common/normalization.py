# pyright: strict

"""Normalisation helpers shared across agent pipelines."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast


def coerce_sequence(value: object) -> list[Any] | None:
    """Return ``value`` as a list when it is a non-string sequence."""

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        result: list[Any] = []
        for item in value:
            result.append(item)
        return result
    return None


def sequence_length(value: object) -> int | None:
    """Return the length of ``value`` when it is a sequence."""

    items = coerce_sequence(value)
    return len(items) if items is not None else None


def coerce_mapping(value: object) -> dict[str, Any]:
    """Return ``value`` as a ``dict`` with string keys when it is mapping-like."""

    if isinstance(value, Mapping):
        mapping_value = cast(Mapping[object, Any], value)
        result: dict[str, Any] = {}
        for key, item in mapping_value.items():
            result[str(key)] = item
        return result
    return {}


def coerce_mapping_list(value: object) -> list[dict[str, Any]]:
    """Return a list of dictionaries derived from ``value`` when possible."""

    items = coerce_sequence(value)
    if items is None:
        return []
    result: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, Mapping):
            mapping_item = cast(Mapping[object, Any], item)
            normalized: dict[str, Any] = {}
            for key, entry in mapping_item.items():
                normalized[str(key)] = entry
            result.append(normalized)
    return result


__all__ = [
    "coerce_sequence",
    "sequence_length",
    "coerce_mapping",
    "coerce_mapping_list",
]
