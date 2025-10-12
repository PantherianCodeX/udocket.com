from __future__ import annotations

# pyright: strict

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..utils.json import (
    JSONObject,
    JSONValue,
    coerce_bool,
    coerce_float,
    coerce_int,
    coerce_json_object,
    coerce_str,
    coerce_str_list,
    load_json_object,
)

BASE_DIR = Path(__file__).resolve().parents[3]
PROVIDERS_PATH = BASE_DIR / "config" / "llm_providers.json"
ASSIGNMENTS_PATH = BASE_DIR / "config" / "llm_assignments.json"


def _empty_json_mapping() -> dict[str, JSONValue]:
    """Return an empty JSON object with a precise type for default factories."""

    return {}


def _empty_str_list() -> list[str]:
    return []


def _empty_str_dict() -> dict[str, str]:
    return {}


@dataclass(frozen=True)
class LLMProviderModel:
    name: str
    label: str
    cost_tier: str
    max_output_tokens: Optional[int] = None
    context_window_tokens: Optional[int] = None
    max_input_tokens: Optional[int] = None
    max_chunk_chars: Optional[int] = None
    chunk_overlap_tokens: Optional[int] = None
    max_prompt_chars: Optional[int] = None
    max_prompt_segments: Optional[int] = None
    default_temperature: Optional[float] = None
    deployment_env: Optional[str] = None
    origin: Optional[str] = None
    default_enabled: bool = True
    options: dict[str, JSONValue] = field(default_factory=_empty_json_mapping)


@dataclass(frozen=True)
class LLMProvider:
    name: str
    display_name: str
    models: dict[str, LLMProviderModel]
    env_requirements: list[str] = field(default_factory=_empty_str_list)
    api_kind: str = "openai"
    default_endpoint: str = ""
    requires_api_key: bool = True
    description: str = ""
    category: str = "creator"
    hosted_creators: list[str] = field(default_factory=_empty_str_list)

    def is_available(self) -> bool:
        return all(os.getenv(key) for key in self.env_requirements)


@dataclass(frozen=True)
class LLMStageAssignment:
    stage_key: str
    providers: list[str]
    model: str
    options: dict[str, str] = field(default_factory=_empty_str_dict)
    target: str = ""
    label: str = ""
    description: str = ""


@dataclass(frozen=True)
class LLMSettings:
    providers: dict[str, LLMProvider]
    assignments: dict[str, LLMStageAssignment]

    def provider(self, name: str) -> Optional[LLMProvider]:
        return self.providers.get(name)

    def stage(self, stage_key: str) -> Optional[LLMStageAssignment]:
        return self.assignments.get(stage_key)

    def all_stage_keys(self) -> list[str]:
        return list(self.assignments.keys())

    def stage_targets(self) -> dict[str, list[str]]:
        targets: dict[str, list[str]] = {}
        for assignment in self.assignments.values():
            target = (assignment.target or "").strip().lower()
            if not target:
                continue
            bucket = targets.setdefault(target, [])
            for stage_key in (assignment.stage_key,):
                if stage_key and stage_key not in bucket:
                    bucket.append(stage_key)
        for target, keys in list(targets.items()):
            targets[target] = sorted(keys)
        return targets

    def stage_keys_for_target(self, target: str) -> list[str]:
        normalized = (target or "").strip().lower()
        if not normalized:
            return []
        return list(self.stage_targets().get(normalized, []))


def _load_json(path: Path) -> JSONObject:
    if not path.exists():
        return {}
    payload = load_json_object(path, context=str(path))
    return {str(key): value for key, value in payload.items()}


def load_llm_settings(
    providers_path: Path = PROVIDERS_PATH,
    assignments_path: Path = ASSIGNMENTS_PATH,
) -> LLMSettings:
    providers_root = coerce_json_object(_load_json(providers_path).get("providers"))
    provider_map: dict[str, LLMProvider] = {}
    for name, provider_payload_raw in providers_root.items():
        provider_payload = coerce_json_object(provider_payload_raw)
        models_payload = coerce_json_object(provider_payload.get("models"))
        models: dict[str, LLMProviderModel] = {}
        for model_name, model_cfg_raw in models_payload.items():
            model_cfg = coerce_json_object(model_cfg_raw)
            options_payload = coerce_json_object(model_cfg.get("options"))
            model_options: dict[str, JSONValue] = {
                str(key): value for key, value in options_payload.items()
            }
            default_enabled_value = coerce_bool(model_cfg.get("default_enabled"), default=True)
            default_enabled = True if default_enabled_value is None else default_enabled_value
            models[model_name] = LLMProviderModel(
                name=model_name,
                label=coerce_str(model_cfg.get("label")) or model_name,
                cost_tier=coerce_str(model_cfg.get("cost_tier")) or "standard",
                max_output_tokens=coerce_int(model_cfg.get("max_output_tokens")),
                context_window_tokens=coerce_int(model_cfg.get("context_window_tokens")),
                max_input_tokens=coerce_int(model_cfg.get("max_input_tokens")),
                max_chunk_chars=coerce_int(model_cfg.get("max_chunk_chars")),
                chunk_overlap_tokens=coerce_int(model_cfg.get("chunk_overlap_tokens")),
                max_prompt_chars=coerce_int(model_cfg.get("max_prompt_chars")),
                max_prompt_segments=coerce_int(model_cfg.get("max_prompt_segments")),
                default_temperature=coerce_float(model_cfg.get("default_temperature")),
                deployment_env=coerce_str(model_cfg.get("deployment_env")),
                origin=coerce_str(model_cfg.get("origin")),
                default_enabled=default_enabled,
                options=model_options,
            )

        hosted_creators: list[str] = coerce_str_list(provider_payload.get("hosted_creators"))
        env_requirements: list[str] = coerce_str_list(provider_payload.get("env_requirements"))
        requires_api_key_value = coerce_bool(provider_payload.get("requires_api_key"), default=True)
        requires_api_key = True if requires_api_key_value is None else requires_api_key_value

        provider_map[name] = LLMProvider(
            name=name,
            display_name=coerce_str(provider_payload.get("display_name")) or name.title(),
            models=models,
            env_requirements=env_requirements,
            api_kind=coerce_str(provider_payload.get("api_kind")) or "openai",
            default_endpoint=coerce_str(provider_payload.get("default_endpoint")) or "",
            requires_api_key=requires_api_key,
            description=coerce_str(provider_payload.get("description")) or "",
            category=coerce_str(provider_payload.get("category")) or "creator",
            hosted_creators=hosted_creators,
        )

    assignments_root = coerce_json_object(_load_json(assignments_path).get("stages"))
    assignment_map: dict[str, LLMStageAssignment] = {}
    for stage_key, assignment_payload_raw in assignments_root.items():
        assignment_payload = coerce_json_object(assignment_payload_raw)
        providers: list[str] = coerce_str_list(assignment_payload.get("providers"))
        model = coerce_str(assignment_payload.get("model")) or ""
        options_payload = coerce_json_object(assignment_payload.get("options"))
        options: dict[str, str] = {key: str(value) for key, value in options_payload.items()}
        target = coerce_str(assignment_payload.get("target")) or stage_key.split(".", 1)[0]
        label = coerce_str(assignment_payload.get("label")) or stage_key
        description = coerce_str(assignment_payload.get("description")) or ""
        assignment_map[stage_key] = LLMStageAssignment(
            stage_key=stage_key,
            providers=providers,
            model=model,
            options=options,
            target=target,
            label=label,
            description=description,
        )

    return LLMSettings(providers=provider_map, assignments=assignment_map)


__all__ = [
    "LLMProviderModel",
    "LLMProvider",
    "LLMStageAssignment",
    "LLMSettings",
    "load_llm_settings",
]
