# pyright: strict
"""Typed helpers for LangGraph stage override payloads."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import cast

from packages.common.agents.stage_map import StageKey
from packages.common.json_utils import JSONObject, coerce_json_object


def _default_json_object() -> JSONObject:
    return {}


def _normalize_provider(value: str) -> str:
    return value.strip().lower()


def _coerce_string(value: object) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _coerce_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            try:
                return int(stripped)
            except ValueError:
                return None
    if isinstance(value, float):
        return int(value)
    return None


@dataclass(frozen=True)
class StageOverrideConfig:
    """Normalized provider/model override for a single stage."""

    providers: tuple[str, ...] = ()
    model: str | None = None
    options: JSONObject = field(default_factory=_default_json_object)
    max_tokens: int | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> StageOverrideConfig:
        providers: list[str] = []
        providers_value = payload.get("providers")
        if isinstance(providers_value, str):
            providers.append(_normalize_provider(providers_value))
        elif isinstance(providers_value, (list, tuple, set)):
            iterable_candidates = cast("Iterable[object]", providers_value)
            string_entries: list[str] = []
            for candidate in iterable_candidates:
                if isinstance(candidate, str):
                    string_entries.append(candidate)
            for entry in string_entries:
                normalized = _normalize_provider(entry)
                if normalized:
                    providers.append(normalized)
        single_provider = payload.get("provider")
        if isinstance(single_provider, str):
            normalized = _normalize_provider(single_provider)
            if normalized:
                providers.append(normalized)

        model = _coerce_string(payload.get("model"))

        options_payload = payload.get("options")
        options: JSONObject
        if isinstance(options_payload, Mapping):
            mapping_options = cast("Mapping[object, object]", options_payload)
            normalized_options: dict[str, object] = {}
            for key_obj, value_obj in mapping_options.items():
                key_text = str(key_obj)
                normalized_options[key_text] = value_obj
            options = coerce_json_object(normalized_options)
        else:
            options = {}

        max_tokens = _coerce_int(payload.get("max_tokens") or payload.get("max_output_tokens"))
        if max_tokens is not None and max_tokens <= 0:
            max_tokens = None

        return cls(
            providers=tuple(dict.fromkeys(providers)),
            model=model,
            options=dict(options),
            max_tokens=max_tokens,
        )

    def to_json(self) -> JSONObject:
        payload: JSONObject = {}
        if self.providers:
            payload["providers"] = list(self.providers)
        if self.model:
            payload["model"] = self.model
        if self.options:
            payload["options"] = dict(self.options)
        if self.max_tokens:
            payload["max_tokens"] = self.max_tokens
        return payload


def _alias_tokens(value: str) -> set[str]:
    normalized = value.lower()
    aliases = {
        normalized,
        normalized.replace(".", "_"),
        normalized.replace("_", "."),
    }
    return {alias for alias in aliases if alias}


def _strip_stage_token(value: str) -> str:
    return value.replace(".", "").replace("_", "")


def _coerce_stage_key(raw_key: str) -> StageKey | None:
    probe = raw_key.strip().lower()
    if not probe:
        return None
    flat_probe = _strip_stage_token(probe)
    for stage_key in StageKey:
        candidates = _alias_tokens(stage_key.value)
        candidates.add(stage_key.name.lower())
        suffix = stage_key.value.split(".", 1)[-1]
        candidates.update(_alias_tokens(suffix))
        flattened = {_strip_stage_token(candidate) for candidate in candidates}
        if probe in candidates or flat_probe in flattened:
            return stage_key
    return None


def parse_stage_overrides(payload: Mapping[str, object] | None) -> dict[StageKey, StageOverrideConfig]:
    if not payload:
        return {}
    overrides: dict[StageKey, StageOverrideConfig] = {}
    for raw_key, raw_value in payload.items():
        if not isinstance(raw_value, Mapping):
            continue
        stage_key = _coerce_stage_key(raw_key)
        if stage_key is None:
            continue
        normalized_payload: dict[str, object] = {}
        mapping_payload = cast("Mapping[object, object]", raw_value)
        for key_obj, value_obj in mapping_payload.items():
            normalized_payload[str(key_obj)] = value_obj
        overrides[stage_key] = StageOverrideConfig.from_payload(normalized_payload)
    return overrides


def stage_overrides_to_json(overrides: Mapping[StageKey, StageOverrideConfig]) -> dict[str, JSONObject]:
    return {stage_key.value: override.to_json() for stage_key, override in overrides.items()}


def stage_overrides_by_name(
    overrides: Mapping[StageKey, StageOverrideConfig] | None,
) -> dict[str, StageOverrideConfig]:
    """Return overrides keyed by canonical stage identifiers."""

    if not overrides:
        return {}
    return {stage_key.value: override for stage_key, override in overrides.items()}


def normalize_stage_override_mapping(
    overrides: Mapping[str | StageKey, StageOverrideConfig] | None,
) -> dict[str, StageOverrideConfig]:
    """Return a canonical mapping keyed by fully qualified stage identifiers."""

    if not overrides:
        return {}
    normalized: dict[str, StageOverrideConfig] = {}
    for key, override in overrides.items():
        if isinstance(key, StageKey):
            normalized[key.value] = override
            continue
        identifier = str(key or "").strip()
        if not identifier:
            continue
        stage_key = _coerce_stage_key(identifier)
        if stage_key is not None:
            normalized[stage_key.value] = override
        else:
            normalized[identifier] = override
    return normalized
