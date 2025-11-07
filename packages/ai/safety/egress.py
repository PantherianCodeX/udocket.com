# pyright: strict

"""Egress policy guardrail helpers."""

from __future__ import annotations

from dataclasses import dataclass

from packages.ai.errors import EgressPolicyError
from packages.ai.types.identifiers import ProviderName


@dataclass(slots=True, frozen=True)
class EgressPolicy:
    """Enforces allow/deny rules for provider egress."""

    allowed_providers: tuple[ProviderName, ...]

    def assert_allowed(self, provider: ProviderName) -> None:
        if self.allowed_providers and provider not in self.allowed_providers:
            raise EgressPolicyError(provider=provider, reason="Provider not permitted")

    @classmethod
    def from_list(cls, providers: tuple[str, ...] | list[str] | None) -> EgressPolicy:
        values = tuple(
            ProviderName(provider.strip())
            for provider in (providers or ())
            if provider and provider.strip()
        )
        return cls(values)


__all__ = ["EgressPolicy"]
