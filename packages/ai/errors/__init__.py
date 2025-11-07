from __future__ import annotations

from dataclasses import dataclass

from ..types import AgentTask, Region
from ..types.identifiers import CapabilityName, ProviderName


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


@dataclass(eq=False)
class ProviderConfigurationError(AIError):
    """Raised when provider credentials or endpoints are invalid."""

    provider: ProviderName
    detail: str

    def __str__(self) -> str:
        return f"{self.detail} (provider={self.provider})"


@dataclass(eq=False)
class ResidencyViolationError(AIError):
    """Raised when a request attempts to use a disallowed region."""

    region: Region
    detail: str = "Requested region is not allowed for this tenant."

    def __str__(self) -> str:
        return f"{self.detail} (region={self.region})"


@dataclass(eq=False)
class EgressPolicyError(AIError):
    """Raised when policy guards prohibit sending the payload to a provider."""

    provider: ProviderName
    reason: str

    def __str__(self) -> str:
        return f"Egress blocked for provider={self.provider}: {self.reason}"


@dataclass(eq=False)
class CapabilityLimitExceeded(AIError):
    """Raised when concurrency or quota limits would be exceeded."""

    task: AgentTask
    capability: CapabilityName
    detail: str = "Capability limit exceeded."

    def __str__(self) -> str:
        return f"{self.detail} (task={self.task.value}, capability={self.capability})"


__all__ = [
    "AIError",
    "ProviderNotConfiguredError",
    "RouteNotFoundError",
    "ProviderConfigurationError",
    "ResidencyViolationError",
    "EgressPolicyError",
    "CapabilityLimitExceeded",
]
