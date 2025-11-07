from __future__ import annotations

# pyright: strict

"""Safety filter interfaces for prompts and responses."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(slots=True, frozen=True)
class SafetyFilterResult:
    """Represents sanitized content and any applied masks."""

    content: str
    redactions: tuple[str, ...]


@runtime_checkable
class SafetyFilter(Protocol):
    """Protocol for prompt/response safety filters."""

    def clean(self, *, content: str) -> SafetyFilterResult: ...


__all__ = ["SafetyFilter", "SafetyFilterResult"]
