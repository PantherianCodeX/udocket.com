from __future__ import annotations

# pyright: strict

"""Egress policy guardrail helpers."""

from dataclasses import dataclass
from typing import Collection

from ..errors import EgressPolicyError
from ..types.identifiers import ProviderName


@dataclass(slots=True, frozen=True)
class EgressPolicy:
    """Enforces allow/deny rules for provider egress."""

    allowed_providers: tuple[ProviderName, ...]

    def assert_allowed(self, provider: ProviderName) -> None:
        if provider not in self.allowed_providers:
            raise EgressPolicyError(provider=provider, reason="Provider not permitted")

    @classmethod
    def from_list(cls, providers: Collection[str] | None) -> EgressPolicy:
        values = tuple(ProviderName(provider) for provider in (providers or ()))
        return cls(values or (ProviderName("azure-openai"),))


__all__ = ["EgressPolicy"]
