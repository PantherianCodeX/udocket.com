# pyright: strict

"""Residency policy interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from packages.ai.errors import ResidencyViolationError

if TYPE_CHECKING:
    from packages.ai.types import AgentTask, AllowedRegion, Region
    from packages.ai.types.identifiers import OrganizationID, ProviderName


@runtime_checkable
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
        _ = (task, org_id)
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
        _ = (provider, region, task, org_id)


__all__ = [
    "AllowAllResidencyPolicy",
    "AllowListResidencyPolicy",
    "ResidencyPolicy",
]
