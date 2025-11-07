from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from .types import AgentTask, LanguageCode, Region
from .types.identifiers import ModelName, ProviderName
from .utils import ensure_language

DEFAULT_ROUTED_TASKS: tuple[AgentTask, ...] = (
    AgentTask.SUMMARIZE,
    AgentTask.OUTLINE,
    AgentTask.TIMELINE,
    AgentTask.ENTITIES,
    AgentTask.RELATIONSHIP,
    AgentTask.COMPOSE,
    AgentTask.QA_REVIEW,
    AgentTask.CHAT,
    AgentTask.EMBED,
)


@dataclass(frozen=True)
class ProviderAccount:
    """Configuration for a single AI provider account."""

    name: ProviderName
    provider_type: str
    region: Region
    endpoint: str | None = None
    default_model: ModelName | None = None
    api_key_env: str | None = None


@dataclass(frozen=True)
class ModelRoute:
    """Maps a task to a provider/model pair."""

    task: AgentTask
    provider: ProviderName
    model: ModelName


@dataclass(frozen=True)
class CapabilityLimit:
    """Concurrency/cap limits enforced per task."""

    task: AgentTask
    max_concurrent: int
    daily_requests: int | None = None


@dataclass(frozen=True)
class AISettings:
    """Aggregate AI runtime configuration."""

    providers: tuple[ProviderAccount, ...]
    routes: tuple[ModelRoute, ...]
    capability_limits: tuple[CapabilityLimit, ...]
    default_language: LanguageCode = LanguageCode.EN_CA

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> AISettings:
        """Construct settings from environment variables."""

        data = dict(env or os.environ)
        region_value = (data.get("AZURE_OPENAI_REGION") or "").strip()
        region = Region(region_value or "default-region")
        provider_name = data.get("UDOCKET_AI_PROVIDER", "azure-openai")
        default_model_value = data.get("UDOCKET_AI_MODEL", "gpt-4o")
        model_name = ModelName(default_model_value)
        provider = ProviderAccount(
            name=ProviderName(provider_name),
            provider_type="azure-openai" if "azure" in provider_name else provider_name,
            region=region,
            endpoint=data.get("AZURE_OPENAI_ENDPOINT"),
            default_model=model_name,
            api_key_env=data.get("UDOCKET_AI_KEY_ENV", "AZURE_OPENAI_KEY"),
        )
        routes = tuple(
            ModelRoute(task=task, provider=provider.name, model=model_name)
            for task in DEFAULT_ROUTED_TASKS
        )
        caps = (
            CapabilityLimit(task=AgentTask.COMPOSE, max_concurrent=1),
            CapabilityLimit(task=AgentTask.SUMMARIZE, max_concurrent=2),
        )
        default_language = ensure_language(data.get("UDOCKET_AI_DEFAULT_LANGUAGE"))
        return cls(
            providers=(provider,),
            routes=routes,
            capability_limits=caps,
            default_language=default_language,
        )


def load_settings(env: Mapping[str, str] | None = None) -> AISettings:
    """Convenience wrapper for constructing AISettings."""

    return AISettings.from_env(env)


__all__ = [
    "AISettings",
    "CapabilityLimit",
    "DEFAULT_ROUTED_TASKS",
    "ModelRoute",
    "ProviderAccount",
    "load_settings",
]
