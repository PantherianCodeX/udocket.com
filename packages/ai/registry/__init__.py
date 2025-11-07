# pyright: strict

"""Helpers for constructing DefaultAIClient instances."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.ai.client import DefaultAIClient
from packages.ai.config import load_settings

if TYPE_CHECKING:
    from collections.abc import Mapping

    from packages.ai.config import AISettings
    from packages.ai.providers.interfaces import ProviderAdapter
    from packages.ai.safety.egress import EgressPolicy
    from packages.ai.safety.residency import ResidencyPolicy
    from packages.ai.types.identifiers import ProviderName


def build_client(
    providers: Mapping[ProviderName, ProviderAdapter],
    *,
    settings: AISettings | None = None,
    residency_policy: ResidencyPolicy | None = None,
    egress_policy: EgressPolicy | None = None,
) -> DefaultAIClient:
    resolved_settings = settings or load_settings()
    return DefaultAIClient(
        settings=resolved_settings,
        providers=providers,
        residency_policy=residency_policy,
        egress_policy=egress_policy,
    )


__all__ = ["build_client"]
