from __future__ import annotations

from pathlib import Path

from packages.udocket_common import json_utils as ju


def test_coerce_json_object_handles_mapping() -> None:
    payload = ju.coerce_json_object({"a": 1, "b": ["x", 2]})
    assert payload == {"a": 1, "b": ["x", 2]}


def test_ensure_json_object_raises_on_invalid() -> None:
    try:
        ju.ensure_json_object(123, context="demo")
    except ValueError as exc:
        assert "demo" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected ValueError")


def test_write_and_read_json(tmp_path: Path) -> None:
    target = tmp_path / "payload.json"
    ju.write_json_object(target, {"hello": "world"})
    data = ju.read_json_object(target)
    assert data == {"hello": "world"}


def test_stringify_json_pretty() -> None:
    rendered = ju.stringify_pretty({"b": 2, "a": 1})
    assert "\n" in rendered
    assert "a" in rendered and "b" in rendered


def test_normalize_mapping_identity() -> None:
    result = ju.normalize_mapping({"A": 1, 2: "two"})
    assert result == {"A": 1, "2": "two"}


def test_normalize_mapping_with_transform() -> None:
    result = ju.normalize_mapping({"A": 1, "B": 2}, transform=lambda value: value * 10)
    assert result == {"A": 10, "B": 20}


def test_normalize_mapping_optional_handles_non_mapping() -> None:
    assert ju.normalize_mapping_optional(123) == {}
    assert ju.normalize_mapping_optional({"k": "v"}) == {"k": "v"}
