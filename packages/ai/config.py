from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from .types import AgentTask, LanguageCode
from .utils import ensure_language


@dataclass(frozen=True)
class ProviderAccount:
    """Configuration for a single AI provider account."""

    name: str
    provider_type: str
    region: str
    endpoint: str | None = None
    default_model: str | None = None
    api_key_env: str | None = None


@dataclass(frozen=True)
class ModelRoute:
    """Maps a task to a provider/model pair."""

    task: AgentTask
    provider: str
    model: str


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
        region = data.get("AZURE_OPENAI_REGION", "canadacentral")
        provider_name = data.get("UDOCKET_AI_PROVIDER", "azure-openai")
        default_model = data.get("UDOCKET_AI_MODEL", "gpt-4o")
        provider = ProviderAccount(
            name=provider_name,
            provider_type="azure-openai" if "azure" in provider_name else provider_name,
            region=region,
            endpoint=data.get("AZURE_OPENAI_ENDPOINT"),
            default_model=default_model,
            api_key_env=data.get("UDOCKET_AI_KEY_ENV", "AZURE_OPENAI_KEY"),
        )
        routes = tuple(
            ModelRoute(task=task, provider=provider.name, model=default_model)
            for task in (
                AgentTask.SUMMARIZE,
                AgentTask.COMPOSE,
                AgentTask.TIMELINE,
                AgentTask.RELATIONSHIP,
                AgentTask.CHAT,
                AgentTask.EMBED,
            )
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


__all__ = [
    "AISettings",
    "CapabilityLimit",
    "ModelRoute",
    "ProviderAccount",
]
