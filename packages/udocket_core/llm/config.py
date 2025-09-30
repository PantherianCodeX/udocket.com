from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

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
    default_temperature: Optional[float] = None
    deployment_env: Optional[str] = None


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


def load_llm_settings(
    providers_path: Path = PROVIDERS_PATH,
    assignments_path: Path = ASSIGNMENTS_PATH,
) -> LLMSettings:
    providers_payload = _load_json(providers_path).get("providers", {})
    provider_map: Dict[str, LLMProvider] = {}
    for name, payload in providers_payload.items():
        models_payload = payload.get("models", {})
        models: Dict[str, LLMProviderModel] = {}
        for model_name, model_cfg in models_payload.items():
            models[model_name] = LLMProviderModel(
                name=model_name,
                label=model_cfg.get("label", model_name),
                cost_tier=model_cfg.get("cost_tier", "standard"),
                max_output_tokens=model_cfg.get("max_output_tokens"),
                context_window_tokens=model_cfg.get("context_window_tokens"),
                default_temperature=model_cfg.get("default_temperature"),
                deployment_env=model_cfg.get("deployment_env"),
            )
        provider_map[name] = LLMProvider(
            name=name,
            display_name=payload.get("display_name", name.title()),
            models=models,
            env_requirements=list(payload.get("env_requirements", [])),
            api_kind=str(payload.get("api_kind") or "openai"),
            default_endpoint=str(payload.get("default_endpoint") or ""),
            requires_api_key=bool(payload.get("requires_api_key", True)),
            description=str(payload.get("description") or ""),
        )

    assignments_payload = _load_json(assignments_path).get("stages", {})
    assignment_map: Dict[str, LLMStageAssignment] = {}
    for stage_key, payload in assignments_payload.items():
        providers = payload.get("providers") or []
        model = payload.get("model")
        options = payload.get("options") or {}
        target = payload.get("target") or stage_key.split(".", 1)[0]
        label = payload.get("label") or stage_key
        description = payload.get("description") or ""
        assignment_map[stage_key] = LLMStageAssignment(
            stage_key=stage_key,
            providers=[str(p) for p in providers if isinstance(p, str)],
            model=str(model) if model else "",
            options={str(k): str(v) for k, v in options.items()},
            target=str(target),
            label=str(label),
            description=str(description),
        )

    return LLMSettings(providers=provider_map, assignments=assignment_map)
