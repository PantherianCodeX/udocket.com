from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

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


def test_json_payload_coerces_values() -> None:
    payload = ju.json_payload(number=1, nested={"x": 2}, list_value=[1, "a"], none_value=None)
    assert payload == {
        "number": 1,
        "nested": {"x": 2},
        "list_value": [1, "a"],
        "none_value": None,
    }


def test_coerce_json_value_handles_custom_object() -> None:
    class Custom:
        def __str__(self) -> str:
            return "custom-object"

    assert ju.coerce_json_value(Custom()) == "custom-object"


def test_coerce_json_object_returns_default_copy() -> None:
    default: ju.JSONObject = {"foo": "bar"}
    result = ju.coerce_json_object("nope", default=default)
    assert result == default
    assert result is not default


def test_merge_json_objects_skips_non_mappings() -> None:
    merged = ju.merge_json_objects({"a": 1}, ["ignored"], {"b": {"c": 3}})
    assert merged == {"a": 1, "b": {"c": 3}}


def test_json_object_to_dict_casts_values() -> None:
    payload: ju.JSONObject = {"a": 1, "b": ["c"]}
    result = ju.json_object_to_dict(payload)
    assert result["b"] == ["c"]


def test_normalize_mapping_optional_with_transform() -> None:
    result = ju.normalize_mapping_optional({"a": 1, "b": 2}, transform=lambda value: value * 2)
    assert result == {"a": 2, "b": 4}


def test_coerce_object_dict_filters_keys_and_values() -> None:
    source = {"": "ignored", "Keep": None, "lower": "VALUE"}
    result = ju.coerce_object_dict(
        source,
        key_transform=lambda key: key.lower(),
        drop_empty_keys=True,
        drop_none_values=True,
    )
    assert result == {"lower": "VALUE"}


def test_normalize_json_object_strips_and_drops() -> None:
    result = ju.normalize_json_object(
        {" key ": " value ", "empty": "", "none": None, "list": []},
        strip_keys=True,
        drop_empty_keys=True,
        drop_nullish_values=True,
    )
    assert result == {"key": " value "}


def test_ensure_json_object_success() -> None:
    payload = {"a": 1}
    assert ju.ensure_json_object(payload) == {"a": 1}


def test_coerce_json_array_handles_sequences() -> None:
    result = ju.coerce_json_array(("a", 2))
    assert result == ["a", 2]
    assert ju.coerce_json_array("not-seq") == []


def test_coerce_object_list_filters_non_mappings() -> None:
    source: list[Any] = [{"a": 1}, "ignore", {"b": 2}]
    result = ju.coerce_object_list(source)
    assert result == [{"a": 1}, {"b": 2}]


def test_coerce_str_dict_options() -> None:
    source = {" Name ": " Value ", "": "ignored", "Empty": "   "}
    result = ju.coerce_str_dict(source, lower_keys=True, value_drop_empty=True)
    assert result == {"name": "Value"}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (" TEXT ", "TEXT"),
        ("   ", None),
        (123, "123"),
    ],
)
def test_coerce_str_variants(value: object, expected: str | None) -> None:
    assert ju.coerce_str(value) == expected


def test_coerce_str_list_normalization() -> None:
    values = [" Alpha ", "beta", "ALPHA "]
    assert ju.coerce_str_list(values, unique=True, lower=True) == ["alpha", "beta"]
    assert ju.coerce_str_list("single") == ["single"]


@pytest.mark.parametrize(
    ("value", "kwargs", "expected"),
    [
        (True, {}, 1),
        (" 5 ", {}, 5),
        ("bad", {"default": 3}, 3),
        (1, {"minimum": 5}, 5),
        (10, {"maximum": 3}, 3),
    ],
)
def test_coerce_int_variants(
    value: object,
    kwargs: dict[str, int | None],
    expected: int | None,
) -> None:
    result = ju.coerce_int(value, **kwargs)
    assert result == expected


@pytest.mark.parametrize(
    ("value", "kwargs", "expected"),
    [
        (False, {}, 0.0),
        (" 2.5 ", {}, 2.5),
        ("oops", {"default": 1.5}, 1.5),
        (1.0, {"minimum": 5.0}, 5.0),
        (10.0, {"maximum": 3.0}, 3.0),
    ],
)
def test_coerce_float_variants(
    value: object,
    kwargs: dict[str, float | None],
    expected: float | None,
) -> None:
    result = ju.coerce_float(value, **kwargs)
    assert result == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True),
        (0, False),
        ("YES", True),
        (" no ", False),
        ("unknown", None),
    ],
)
def test_coerce_bool_variants(value: object, expected: bool | None) -> None:
    assert ju.coerce_bool(value) == expected


def test_read_json_value_handles_missing(tmp_path: Path) -> None:
    missing = tmp_path / "not-there.json"
    assert ju.read_json_value(missing) is None


def test_read_json_value_handles_invalid(tmp_path: Path) -> None:
    target = tmp_path / "broken.json"
    target.write_text("{not valid", encoding="utf-8")
    assert ju.read_json_value(target) is None


def test_read_json_object_with_default(tmp_path: Path) -> None:
    target = tmp_path / "object.json"
    target.write_text("[]", encoding="utf-8")
    assert ju.read_json_object(target, default={"fallback": 1}) == {"fallback": 1}


def test_write_json_value_scalar(tmp_path: Path) -> None:
    target = tmp_path / "value.json"
    ju.write_json_value(target, "scalar")
    assert target.read_text(encoding="utf-8") == '"scalar"'


def test_parse_json_value_success_and_failure() -> None:
    assert ju.parse_json_value('{"a": 1}') == {"a": 1}
    assert ju.parse_json_value("not json") is None


def test_parse_json_value_strict_errors() -> None:
    with pytest.raises(ValueError, match="payload"):
        ju.parse_json_value_strict("oops", context="payload")


def test_parse_json_object_requires_mapping() -> None:
    with pytest.raises(ValueError):
        ju.parse_json_object("[]", context="payload")


def test_load_json_object_errors(tmp_path: Path) -> None:
    target = tmp_path / "missing.json"
    with pytest.raises(ValueError):
        ju.load_json_object(target, context="missing")


def test_load_json_value(tmp_path: Path) -> None:
    target = tmp_path / "value.json"
    target.write_text('{"a": 1}', encoding="utf-8")
    value = ju.load_json_value(target)
    assert isinstance(value, dict)
    assert value["a"] == 1


def test_stringify_json_respects_indent() -> None:
    rendered = ju.stringify_json({"a": 1}, indent=0, sort_keys=True)
    assert rendered.startswith("{")
    assert '"a"' in rendered
