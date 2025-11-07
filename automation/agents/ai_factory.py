from __future__ import annotations

# pyright: strict

"""Shared AI client factory for automation modules."""

from functools import lru_cache

from packages.ai import DefaultAIClient, build_client
from packages.ai.config import load_settings
from packages.ai.providers.registry import default_adapters


@lru_cache(maxsize=1)
def get_ai_client() -> DefaultAIClient:
    """Return a cached DefaultAIClient wired with the default adapter registry."""

    settings = load_settings()
    adapters = default_adapters()
    return build_client(adapters, settings=settings)


__all__ = ["get_ai_client"]
