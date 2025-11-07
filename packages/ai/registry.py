from __future__ import annotations

# pyright: strict

"""Helpers for constructing DefaultAIClient instances."""

from collections.abc import Mapping

from .client import DefaultAIClient
from .config import AISettings, load_settings
from .providers.interfaces import ProviderAdapter
from .safety.egress import EgressPolicy
from .safety.residency import ResidencyGuard
from .types.identifiers import ProviderName


def build_client(
    providers: Mapping[ProviderName, ProviderAdapter],
    *,
    settings: AISettings | None = None,
    residency_guard: ResidencyGuard | None = None,
    egress_policy: EgressPolicy | None = None,
) -> DefaultAIClient:
    resolved_settings = settings or load_settings()
    return DefaultAIClient(
        settings=resolved_settings,
        providers=providers,
        residency_guard=residency_guard,
        egress_policy=egress_policy,
    )


__all__ = ["build_client"]
