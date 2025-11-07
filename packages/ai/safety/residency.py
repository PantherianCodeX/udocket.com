from __future__ import annotations

# pyright: strict

"""Residency policy interfaces."""

from dataclasses import dataclass
from typing import Protocol

from ..errors import ResidencyViolationError
from ..types import AgentTask, AllowedRegion, Region
from ..types.identifiers import OrganizationID, ProviderName


class ResidencyPolicy(Protocol):
    """Determines whether a provider/region combination is permitted."""

    def assert_allowed(
        self,
        *,
        provider: ProviderName,
        region: Region,
        task: AgentTask,
        org_id: OrganizationID | None = None,
    ) -> None: ...


@dataclass(slots=True, frozen=True)
class AllowListResidencyPolicy(ResidencyPolicy):
    """Residency policy backed by an allow list."""

    allowed_regions: tuple[AllowedRegion, ...]

    def assert_allowed(
        self,
        *,
        provider: ProviderName,
        region: Region,
        task: AgentTask,
        org_id: OrganizationID | None = None,
    ) -> None:
        if not self.allowed_regions:
            return
        for rule in self.allowed_regions:
            provider_matches = rule.provider is None or rule.provider == provider
            if provider_matches and rule.region == region:
                return
        raise ResidencyViolationError(region=region)


@dataclass(slots=True, frozen=True)
class AllowAllResidencyPolicy(ResidencyPolicy):
    """Residency policy that permits every region (useful for tests/dev)."""

    def assert_allowed(
        self,
        *,
        provider: ProviderName,
        region: Region,
        task: AgentTask,
        org_id: OrganizationID | None = None,
    ) -> None:  # pragma: no cover - trivial
        return None


__all__ = [
    "ResidencyPolicy",
    "AllowListResidencyPolicy",
    "AllowAllResidencyPolicy",
]
