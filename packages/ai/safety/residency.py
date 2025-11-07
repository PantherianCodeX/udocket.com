from __future__ import annotations

# pyright: strict

"""Residency guard helpers."""

from dataclasses import dataclass
from typing import Collection

from ..errors import ResidencyViolationError
from ..types import RegionCode


@dataclass(slots=True, frozen=True)
class ResidencyGuard:
    """Enforces allowed regions per tenant or deployment."""

    allowed_regions: tuple[RegionCode, ...]

    def assert_allowed(self, region: RegionCode) -> None:
        if region not in self.allowed_regions:
            raise ResidencyViolationError(region=region)

    @classmethod
    def canada_only(cls) -> ResidencyGuard:
        return cls(allowed_regions=(RegionCode.CANADA_CENTRAL, RegionCode.CANADA_EAST))

    @classmethod
    def from_config(cls, regions: Collection[str] | None) -> ResidencyGuard:
        values = tuple(RegionCode(region) for region in (regions or []))
        return cls(values or cls.canada_only().allowed_regions)


__all__ = ["ResidencyGuard"]
