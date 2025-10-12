from __future__ import annotations

# pyright: strict

from .utils.json import JSONObject


def json_object_factory() -> JSONObject:
    """Return a new JSON object for dataclass default factories."""

    return {}


def json_object_list_factory() -> list[JSONObject]:
    """Return a new list of JSON objects for dataclass default factories."""

    return []


def str_list_factory() -> list[str]:
    """Return a new list of strings for dataclass default factories."""

    return []


def stage_usage_factory() -> dict[str, dict[str, int]]:
    """Return a new stage usage mapping for dataclass default factories."""

    return {}


def int_usage_factory() -> dict[str, int]:
    """Return a new int usage mapping for dataclass default factories."""

    return {}


def float_usage_factory() -> dict[str, float]:
    """Return a new float usage mapping for dataclass default factories."""

    return {}


__all__ = [
    "json_object_factory",
    "json_object_list_factory",
    "str_list_factory",
    "stage_usage_factory",
    "int_usage_factory",
    "float_usage_factory",
]
