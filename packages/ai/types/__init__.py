from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LanguageCode(StrEnum):
    """Supported language identifiers for AI-powered flows."""

    EN_CA = "en-CA"
    FR_CA = "fr-CA"


class AgentTask(StrEnum):
    """Canonical agent task identifiers used for routing and telemetry."""

    SUMMARIZE = "summarize"
    COMPOSE = "compose"
    TIMELINE = "timeline"
    RELATIONSHIP = "relationship"
    CHAT = "chat"
    EMBED = "embed"


@dataclass(frozen=True)
class CaseContext:
    """Case-scoped identifiers that travel with every AI request."""

    org_id: str
    case_id: str
    job_id: str | None = None


@dataclass(frozen=True)
class ProviderCallMetrics:
    """Structured telemetry returned by provider adapters."""

    total_tokens: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: float | None = None


UUIDStr = str

__all__ = [
    "AgentTask",
    "CaseContext",
    "LanguageCode",
    "ProviderCallMetrics",
    "UUIDStr",
]
