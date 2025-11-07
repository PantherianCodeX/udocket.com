from __future__ import annotations

# pyright: strict

"""Temporary shim bridging legacy agents to the new packages.ai client."""

from functools import lru_cache

from packages.ai import DefaultAIClient, build_client
from packages.ai.config.translator import ai_settings_from_llm
from packages.ai.providers.registry import default_adapters
from packages.core.llm.config import load_llm_settings


@lru_cache(maxsize=1)
def default_ai_client() -> DefaultAIClient:
    """Return a cached DefaultAIClient backed by the null provider registry."""

    llm_settings = load_llm_settings()
    settings = ai_settings_from_llm(llm_settings)
    adapters = default_adapters()
    return build_client(adapters, settings=settings)


__all__ = ["default_ai_client"]
