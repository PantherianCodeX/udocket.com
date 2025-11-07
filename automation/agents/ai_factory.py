# pyright: strict

"""Shared AI client factory for automation modules."""

from __future__ import annotations

from functools import lru_cache

from packages.ai import DefaultAIClient, build_client
from packages.ai.config.translator import ai_settings_from_llm
from packages.ai.providers.registry import adapters_from_settings
from packages.ai.safety.egress import EgressPolicy
from packages.ai.safety.residency import AllowAllResidencyPolicy, ResidencyPolicy
from packages.ai.secret import EnvSecretSource
from packages.core.llm.config import load_llm_settings


@lru_cache(maxsize=1)
def get_ai_client() -> DefaultAIClient:
    """Return a cached DefaultAIClient wired with the default adapter registry."""

    llm_settings = load_llm_settings()
    settings = ai_settings_from_llm(llm_settings)
    residency_policy: ResidencyPolicy = AllowAllResidencyPolicy()
    egress_policy = EgressPolicy.from_list(None)
    secret_source = EnvSecretSource()
    adapters = adapters_from_settings(
        settings,
        secret_source=secret_source,
        residency_policy=residency_policy,
        egress_policy=egress_policy,
    )
    return build_client(
        adapters,
        settings=settings,
        residency_policy=residency_policy,
        egress_policy=egress_policy,
    )


__all__ = ["get_ai_client"]
