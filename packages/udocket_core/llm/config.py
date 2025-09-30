from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, cast

BASE_DIR = Path(__file__).resolve().parents[3]
PROVIDERS_PATH = BASE_DIR / "config" / "llm_providers.json"
ASSIGNMENTS_PATH = BASE_DIR / "config" / "llm_assignments.json"


@dataclass
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
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMProvider:
    name: str
    display_name: str
    models: Dict[str, LLMProviderModel]
    env_requirements: List[str] = field(default_factory=list)
    api_kind: str = "openai"
    default_endpoint: str = ""
    requires_api_key: bool = True
    description: str = ""
    category: str = "creator"
    hosted_creators: List[str] = field(default_factory=list)

    def is_available(self) -> bool:
        return all(os.getenv(key) for key in self.env_requirements)


@dataclass
class LLMStageAssignment:
    stage_key: str
    providers: List[str]
    model: str
    options: Dict[str, str] = field(default_factory=dict)
    target: str = ""
    label: str = ""
    description: str = ""


@dataclass
class LLMSettings:
    providers: Dict[str, LLMProvider]
    assignments: Dict[str, LLMStageAssignment]

    def provider(self, name: str) -> Optional[LLMProvider]:
        return self.providers.get(name)

    def stage(self, stage_key: str) -> Optional[LLMStageAssignment]:
        return self.assignments.get(stage_key)

    def all_stage_keys(self) -> List[str]:
        return list(self.assignments.keys())

    def stage_targets(self) -> Dict[str, List[str]]:
        targets: Dict[str, List[str]] = {}
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

    def stage_keys_for_target(self, target: str) -> List[str]:
        normalized = (target or "").strip().lower()
        if not normalized:
            return []
        return list(self.stage_targets().get(normalized, []))


def _load_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _as_dict(value: object) -> Dict[str, Any]:
    mapping: Mapping[Any, Any]
    if isinstance(value, dict):
        mapping = cast(Mapping[Any, Any], value)
    elif isinstance(value, Mapping):
        mapping = value
    else:
        return {}
    normalized: Dict[str, Any] = {}
    for key, raw in mapping.items():
        normalized[str(key)] = raw
    return normalized


def _as_list(value: object) -> List[Any]:
    if isinstance(value, (list, tuple)):
        iterable = cast(Iterable[Any], value)
        return [element for element in iterable]
    return []


def load_llm_settings(
    providers_path: Path = PROVIDERS_PATH,
    assignments_path: Path = ASSIGNMENTS_PATH,
) -> LLMSettings:
    providers_raw = _load_json(providers_path).get("providers", {})
    providers_payload = _as_dict(providers_raw)
    provider_map: Dict[str, LLMProvider] = {}
    for name, payload_obj in providers_payload.items():
        payload = _as_dict(payload_obj)
        models_payload = _as_dict(payload.get("models", {}))
        models: Dict[str, LLMProviderModel] = {}
        for model_name, model_cfg_obj in models_payload.items():
            model_cfg = _as_dict(model_cfg_obj)
            models[model_name] = LLMProviderModel(
                name=model_name,
                label=model_cfg.get("label", model_name),
                cost_tier=model_cfg.get("cost_tier", "standard"),
                max_output_tokens=model_cfg.get("max_output_tokens"),
                context_window_tokens=model_cfg.get("context_window_tokens"),
                max_input_tokens=model_cfg.get("max_input_tokens"),
                max_chunk_chars=model_cfg.get("max_chunk_chars"),
                chunk_overlap_tokens=model_cfg.get("chunk_overlap_tokens"),
                max_prompt_chars=model_cfg.get("max_prompt_chars"),
                max_prompt_segments=model_cfg.get("max_prompt_segments"),
                default_temperature=model_cfg.get("default_temperature"),
                deployment_env=model_cfg.get("deployment_env"),
                origin=model_cfg.get("origin"),
                default_enabled=bool(
                    model_cfg.get("default_enabled", True)
                ),
                options={
                    str(k): v
                    for k, v in _as_dict(model_cfg.get("options")).items()
                },
            )
        hosted_creators = [
            str(entry)
            for entry in _as_list(payload.get("hosted_creators"))
            if isinstance(entry, (str, int, float))
        ]
        env_requirements = [
            str(item)
            for item in _as_list(payload.get("env_requirements"))
            if isinstance(item, str)
        ]
        provider_map[name] = LLMProvider(
            name=name,
            display_name=payload.get("display_name", name.title()),
            models=models,
            env_requirements=env_requirements,
            api_kind=str(payload.get("api_kind") or "openai"),
            default_endpoint=str(payload.get("default_endpoint") or ""),
            requires_api_key=bool(payload.get("requires_api_key", True)),
            description=str(payload.get("description") or ""),
            category=str(payload.get("category") or "creator"),
            hosted_creators=hosted_creators,
        )

    assignments_raw = _load_json(assignments_path).get("stages", {})
    assignments_payload = _as_dict(assignments_raw)
    assignment_map: Dict[str, LLMStageAssignment] = {}
    for stage_key, payload_obj in assignments_payload.items():
        payload = _as_dict(payload_obj)
        providers_raw = _as_list(payload.get("providers"))
        providers = [str(p) for p in providers_raw if isinstance(p, str)]
        model_value = payload.get("model")
        model = str(model_value) if isinstance(model_value, str) else ""
        options_raw = _as_dict(payload.get("options"))
        options = {str(k): str(v) for k, v in options_raw.items()}
        target = payload.get("target") or stage_key.split(".", 1)[0]
        label = payload.get("label") or stage_key
        description = payload.get("description") or ""
        assignment_map[stage_key] = LLMStageAssignment(
            stage_key=stage_key,
            providers=providers,
            model=model,
            options=options,
            target=str(target),
            label=str(label),
            description=str(description),
        )

    return LLMSettings(providers=provider_map, assignments=assignment_map)
