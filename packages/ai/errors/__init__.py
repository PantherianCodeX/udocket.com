from __future__ import annotations

from dataclasses import dataclass

from .types import AgentTask


class AIError(RuntimeError):
    """Base class for AI runtime errors."""


@dataclass(eq=False)
class ProviderNotConfiguredError(AIError):
    """Raised when an operation is requested without a configured provider."""

    task: AgentTask
    detail: str = "No AI provider configured for the requested task."

    def __str__(self) -> str:
        return f"{self.detail} (task={self.task.value})"


@dataclass(eq=False)
class RouteNotFoundError(AIError):
    """Raised when routing cannot find a model path for the requested task."""

    task: AgentTask
    provider: str | None = None
    detail: str = "No model route available."

    def __str__(self) -> str:
        provider_part = f", provider={self.provider}" if self.provider else ""
        return f"{self.detail} (task={self.task.value}{provider_part})"


__all__ = [
    "AIError",
    "ProviderNotConfiguredError",
    "RouteNotFoundError",
]
