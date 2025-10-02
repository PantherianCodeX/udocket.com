from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence
from urllib.parse import quote

from django.urls import reverse

from apps.platform.cases.models import Case
from packages.udocket_core.agents.compose import COMPOSE_STAGE_PROFILES
from packages.udocket_core.agents.analyze_lib import SUMMARIZE_STAGE_PROFILES, AnalyzeConfig
from packages.udocket_core.llm import load_llm_settings

from apps.platform.operations.llm import (
    build_provider_registry,
    ensure_default_llm_configuration,
    get_llm_configuration,
    get_org_llm_configurations,
    get_org_provider_credentials,
    load_provider_catalog,
)


def collect_provider_chain(provider_chain: Sequence[str], default_chain: Sequence[str]) -> List[str]:
    sequence: List[str] = []
    for name in provider_chain:
        value = str(name or "").strip().lower()
        if value and value not in sequence:
            sequence.append(value)
    for name in default_chain:
        if name not in sequence:
            sequence.append(name)
    return sequence


def _stage_profile_hint(stage_key: str, *, target: str) -> Dict[str, Any] | None:
    if target in {"summary", "analyze"}:
        profile = SUMMARIZE_STAGE_PROFILES.get(stage_key)
    elif target == "compose":
        profile = COMPOSE_STAGE_PROFILES.get(stage_key)
    else:
        profile = None
    if profile is None:
        return None
    return {
        "min_context_tokens": profile.min_context_tokens,
        "recommended_context_tokens": profile.recommended_context_tokens,
        "target_chunk_tokens": profile.target_chunk_tokens,
        "output_reserve_tokens": profile.output_reserve_tokens,
        "resource_notes": profile.resource_notes,
    }


def _stage_definitions_for_target(*, llm_settings, target: str, stage_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, str]]:
    stage_defs: List[Dict[str, str]] = []
    seen: set[str] = set()

    for assignment in llm_settings.assignments.values():
        if assignment.target != target:
            continue
        stage_defs.append(
            {
                "key": assignment.stage_key,
                "label": assignment.label or assignment.stage_key,
                "description": assignment.description,
            }
        )
        seen.add(assignment.stage_key)

    for raw_key in stage_map.keys():
        stage_key = str(raw_key)
        if stage_key in seen:
            continue
        stage_defs.append({"key": stage_key, "label": stage_key, "description": ""})
        seen.add(stage_key)

    return stage_defs


def build_llm_stage_configs(*, target: str, llm_settings, stage_map: Dict[str, Dict[str, Any]], provider_registry: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    stage_map = stage_map or {}
    stage_defs = _stage_definitions_for_target(
        llm_settings=llm_settings,
        target=target,
        stage_map=stage_map,
    )
    stage_configs: List[Dict[str, Any]] = []

    for stage in stage_defs:
        stage_key = stage.get("key")
        stage_label = stage.get("label", stage_key)
        stage_description = stage.get("description", "")
        assignment = llm_settings.stage(stage_key)
        provider_configs = list(provider_registry.values())
        selected_provider = (
            assignment.providers[0]
            if assignment and assignment.providers
            else (provider_configs[0]["value"] if provider_configs else "azure")
        )
        selected_model = assignment.model if assignment and getattr(assignment, "model", None) else ""
        selected_options: Dict[str, Any] = dict(assignment.options) if assignment else {}
        selected_max_tokens: int | None = None

        override_payload = stage_map.get(stage_key)
        if override_payload:
            provider_override = override_payload.get("provider")
            if isinstance(provider_override, str) and provider_override.strip():
                selected_provider = provider_override.strip().lower()
            providers_override = override_payload.get("providers")
            if isinstance(providers_override, list):
                for candidate in providers_override:
                    if isinstance(candidate, str) and candidate.strip():
                        selected_provider = candidate.strip().lower()
                        break
            model_override = override_payload.get("model")
            if isinstance(model_override, str) and model_override.strip():
                selected_model = model_override.strip()
            options_override = override_payload.get("options")
            if isinstance(options_override, dict):
                selected_options.update(options_override)
            max_override = override_payload.get("max_tokens")
            if isinstance(max_override, (int, float)):
                max_value = int(max_override)
                if max_value > 0:
                    selected_max_tokens = max_value

        profile_hint = _stage_profile_hint(stage_key, target=target)
        stage_configs.append(
            {
                "key": stage_key,
                "label": stage_label,
                "description": stage_description,
                "providers": provider_configs,
                "selected_provider": selected_provider,
                "selected_model": selected_model,
                "selected_options": selected_options,
                "selected_max_tokens": selected_max_tokens,
                "profile": profile_hint,
            }
        )
    return stage_configs


def _build_llm_urls(target: str, *, return_url: str, active_config: Dict[str, Any] | None) -> Dict[str, str]:
    encoded_return_url = quote(return_url, safe="")

    def _with_next(url: str) -> str:
        if not encoded_return_url:
            return url
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}next={encoded_return_url}"

    settings_base = reverse("ui-organization-settings-section", args=[target])
    edit_base = (
        f"{settings_base}?config={active_config.get('id')}"
        if active_config and active_config.get("id")
        else settings_base
    )
    return {
        "base": settings_base,
        "edit": _with_next(edit_base),
        "new": _with_next(f"{settings_base}?new=1"),
        "tuning": _with_next(reverse("ui-organization-settings-section", args=["providers"])),
    }


def _configured_stages(stage_configs: List[Dict[str, Any]], stage_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    configured: List[Dict[str, Any]] = []
    for stage in stage_configs:
        override = stage_map.get(stage["key"])
        if not override:
            continue
        configured.append(
            {
                "key": stage["key"],
                "label": stage.get("label") or stage["key"],
                "provider": override.get("provider") or stage.get("selected_provider"),
                "model": override.get("model") or stage.get("selected_model"),
                "max_tokens": override.get("max_tokens"),
                "options": override.get("options") or {},
            }
        )
    return configured


def build_analysis_llm_context(case: Case, *, return_url: str) -> Dict[str, Dict[str, Any]]:
    try:
        analyze_cfg = AnalyzeConfig.from_env()
    except Exception:  # noqa: BLE001
        analyze_cfg = AnalyzeConfig()

    llm_settings = load_llm_settings()
    provider_catalog = load_provider_catalog()
    provider_credentials = get_org_provider_credentials(case.organization_id)
    provider_registry = build_provider_registry(
        organization_id=case.organization_id,
        llm_settings=llm_settings,
        provider_catalog=provider_catalog,
        provider_credentials=provider_credentials,
    )

    default_chain = list(analyze_cfg.provider_chain or ["azure"])

    def _build_target(target: str) -> Dict[str, Any]:
        config_list = get_org_llm_configurations(str(case.organization_id), target=target)
        active_config = get_llm_configuration(
            organization_id=str(case.organization_id),
            config_id=None,
            target=target,
        )
        if not active_config:
            active_config = ensure_default_llm_configuration(
                organization_id=str(case.organization_id),
                target=target,
                llm_settings=llm_settings,
            )
            if active_config:
                config_list = get_org_llm_configurations(str(case.organization_id), target=target)

        stage_map_raw = active_config.get("stage_map", {}) if active_config else {}
        stage_map = dict(stage_map_raw or {})
        stage_configs = build_llm_stage_configs(
            target=target,
            llm_settings=llm_settings,
            stage_map=stage_map,
            provider_registry=provider_registry,
        )
        chain = collect_provider_chain(active_config.get("provider_chain", []) if active_config else [], default_chain)

        return {
            "target": target,
            "configurations": config_list,
            "configurations_json": json.dumps(config_list),
            "active_configuration": active_config,
            "active_configuration_json": json.dumps(active_config or {}),
            "configured_stages": _configured_stages(stage_configs, stage_map),
            "stage_configs": stage_configs,
            "stage_configs_json": json.dumps(stage_configs),
            "stage_map_json": json.dumps(stage_map),
            "provider_chain": chain,
            "provider_chain_json": json.dumps(chain),
            "urls": _build_llm_urls(target, return_url=return_url, active_config=active_config),
            "return_url": return_url,
        }

    return {
        "analyze": _build_target("analyze"),
        "timeline": _build_target("timeline"),
        "compose": _build_target("compose"),
    }


__all__ = [
    "build_analysis_llm_context",
    "build_llm_stage_configs",
    "collect_provider_chain",
]
