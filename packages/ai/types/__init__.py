from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import NewType

from .identifiers import (
    ArtifactID,
    CapabilityName,
    CaseID,
    JobID,
    ModelName,
    OrganizationID,
    ProviderName,
    RouteName,
)

Region = NewType("Region", str)


class LanguageCode(StrEnum):
    """Supported language identifiers for AI-powered flows."""

    EN_CA = "en-CA"
    FR_CA = "fr-CA"


class DataClassification(StrEnum):
    """Data sensitivity classifications that influence policy decisions."""

    GENERAL = "general"
    CONFIDENTIAL = "confidential"
    REGULATED = "regulated"


class AgentTask(StrEnum):
    """Capability-first agent task identifiers used for routing and telemetry."""

    GENERATE = "generate"
    EXTRACT = "extract"
    EVAL = "eval"
    EMBED = "embed"
    ATOMS = "atoms"
    CHAT = "chat"

    # Backwards-compatible aliases (artifact-scoped names map to capabilities)
    SUMMARIZE = "generate"
    OUTLINE = "extract"
    TIMELINE = "extract"
    ENTITIES = "extract"
    RELATIONSHIP = "extract"
    COMPOSE = "generate"
    QA_REVIEW = "eval"


@dataclass(slots=True, frozen=True)
class CaseContext:
    """Case-scoped identifiers that travel with every AI request."""

    org_id: OrganizationID
    case_id: CaseID
    job_id: JobID | None = None
    classification: DataClassification = DataClassification.GENERAL


@dataclass(slots=True, frozen=True)
class AllowedRegion:
    """Typed region constraint passed from org-level settings."""

    region: Region
    provider: ProviderName | None = None


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
    "AllowedRegion",
    "ArtifactID",
    "CapabilityName",
    "CaseContext",
    "DataClassification",
    "LanguageCode",
    "ModelName",
    "OrganizationID",
    "ProviderCallMetrics",
    "ProviderName",
    "Region",
    "RouteName",
    "UUIDStr",
]
