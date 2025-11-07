from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .identifiers import (
    ArtifactID,
    CaseID,
    CapabilityName,
    JobID,
    ModelName,
    OrganizationID,
    ProviderName,
    RouteName,
)

class LanguageCode(StrEnum):
    """Supported language identifiers for AI-powered flows."""

    EN_CA = "en-CA"
    FR_CA = "fr-CA"


class RegionCode(StrEnum):
    """Azure Speech / OpenAI residency-compliant regions."""

    CANADA_CENTRAL = "canadacentral"
    CANADA_EAST = "canadaeast"


class AgentTask(StrEnum):
    """Canonical agent task identifiers used for routing and telemetry."""

    SUMMARIZE = "summarize"
    OUTLINE = "outline"
    TIMELINE = "timeline"
    ENTITIES = "entities"
    RELATIONSHIP = "relationship"  # alias for backward compat
    COMPOSE = "compose"
    QA_REVIEW = "qa_review"
    CHAT = "chat"
    EMBED = "embed"


@dataclass(slots=True, frozen=True)
class CaseContext:
    """Case-scoped identifiers that travel with every AI request."""

    org_id: OrganizationID
    case_id: CaseID
    job_id: JobID | None = None


@dataclass(slots=True, frozen=True)
class ProviderCallMetrics:
    """Structured telemetry returned by provider adapters."""

    total_tokens: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: float | None = None


UUIDStr = str

__all__ = [
    "AgentTask",
    "ArtifactID",
    "CaseContext",
    "CapabilityName",
    "LanguageCode",
    "RegionCode",
    "ModelName",
    "OrganizationID",
    "ProviderCallMetrics",
    "ProviderName",
    "RouteName",
    "UUIDStr",
]
