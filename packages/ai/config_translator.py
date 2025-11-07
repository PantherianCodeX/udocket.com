from __future__ import annotations

# pyright: strict

"""Translates legacy LLM settings into AISettings."""

from collections.abc import Iterable

from packages.core.llm.config import LLMSettings

from .config import AISettings, CapabilityLimit, ModelRoute, ProviderAccount
from .types import AgentTask, AllowedRegion, LanguageCode, Region
from .types.identifiers import ModelName, ProviderName


def ai_settings_from_llm(llm_settings: LLMSettings) -> AISettings:
    """Convert core LLM settings into AISettings."""

    provider_accounts: list[ProviderAccount] = []
    for provider in llm_settings.providers.values():
        default_model_name = _default_model_name(provider.models.keys())
        if not default_model_name:
            continue
        endpoint_region = Region(provider.default_endpoint or "unspecified-region")
        allowed = (AllowedRegion(region=endpoint_region),)
        provider_accounts.append(
            ProviderAccount(
                name=ProviderName(provider.name),
                provider_type=provider.api_kind or provider.name,
                region=endpoint_region,
                endpoint=provider.default_endpoint or "",
                default_model=ModelName(default_model_name),
                api_key_env=(provider.env_requirements[0] if provider.env_requirements else None),
                allowed_regions=allowed,
            )
        )

    routes: list[ModelRoute] = []
    for assignment in llm_settings.assignments.values():
        task = _task_for_stage(assignment.stage_key)
        if task is None:
            continue
        model_name = assignment.model or _default_model_name(assignment.providers)
        if not model_name:
            continue
        for provider_name in assignment.providers or []:
            routes.append(
                ModelRoute(
                    task=task,
                    provider=ProviderName(provider_name),
                    model=ModelName(model_name),
                )
            )
    capability_limits = (
        CapabilityLimit(task=AgentTask.SUMMARIZE, max_concurrent=2),
        CapabilityLimit(task=AgentTask.COMPOSE, max_concurrent=1),
    )
    return AISettings(
        providers=tuple(provider_accounts),
        routes=tuple(routes),
        capability_limits=capability_limits,
        default_language=LanguageCode.EN_CA,
    )


def _default_model_name(model_names: Iterable[str] | None) -> str | None:
    if not model_names:
        return None
    first = next(iter(model_names), None)
    return first


def _task_for_stage(stage_key: str) -> AgentTask | None:
    normalized = stage_key.lower()
    if "compose" in normalized:
        return AgentTask.COMPOSE
    if "timeline" in normalized:
        return AgentTask.TIMELINE
    if "entity" in normalized:
        return AgentTask.ENTITIES
    if "summary" in normalized:
        return AgentTask.SUMMARIZE
    if "context" in normalized:
        return AgentTask.CHAT
    return None


__all__ = ["ai_settings_from_llm"]
