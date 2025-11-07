from __future__ import annotations

# pyright: strict

"""Moderation interface definitions."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(slots=True, frozen=True)
class ModerationVerdict:
    """Represents a moderation response."""

    blocked: bool
    category: str | None = None
    detail: str | None = None


@runtime_checkable
class ModerationClient(Protocol):
    """Protocol for moderation providers."""

    def evaluate(self, *, content: str) -> ModerationVerdict: ...


__all__ = ["ModerationClient", "ModerationVerdict"]
