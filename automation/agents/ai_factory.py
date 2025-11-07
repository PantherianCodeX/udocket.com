from __future__ import annotations

# pyright: strict

"""Shared AI client factory for automation modules."""

from functools import lru_cache

from packages.ai import DefaultAIClient, build_client
from packages.ai.config import load_settings
from packages.ai.providers.registry import default_adapters
from packages.ai.safety.egress import EgressPolicy
from packages.ai.safety.residency import AllowAllResidencyPolicy


@lru_cache(maxsize=1)
def get_ai_client() -> DefaultAIClient:
    """Return a cached DefaultAIClient wired with the default adapter registry."""

    settings = load_settings()
    adapters = default_adapters()
    residency_policy = AllowAllResidencyPolicy()
    egress_policy = EgressPolicy.from_list(None)
    return build_client(
        adapters,
        settings=settings,
        residency_policy=residency_policy,
        egress_policy=egress_policy,
    )


__all__ = ["get_ai_client"]
