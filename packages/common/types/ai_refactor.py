"""Typed models for the AI refactor manifests and ledger entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from uuid import UUID

from packages.common.agents.stage_map import StageKey


class ArtifactOwner(StrEnum):
    ARTIFACT_PLATFORMS = "Platform Architecture"
    ARTIFACT_APPLIED_AI = "Applied AI Engineering"
    ARTIFACT_AUTOMATION = "Automation Engineering"


class ImplementationStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class LaneID(StrEnum):
    TRANSCRIBE = "TRANSCRIBE"
    ANALYZE = "ANALYZE"
    COMPOSE = "COMPOSE"
    TIMELINE = "TIMELINE"
    RELATIONSHIP = "RELATIONSHIP"


class ResidencyTag(StrEnum):
    US_EAST = "US-EAST"
    EU_CENTRAL = "EU-CENTRAL"


class FeatureID(StrEnum):
    REFRACTOR_001 = "001-ai-refactor-plan"
    REFRACTOR_002 = "002-ai-refactor-plan"


@dataclass(frozen=True)
class ResidencyLedgerEntry:
    ledger_id: UUID
    feature_id: FeatureID
    run_id: UUID
    stage_key: StageKey
    residency_tag: ResidencyTag
    telemetry_bundle_path: Path
    langsmith_eval_ids: tuple[UUID, ...]
    langfuse_session_id: UUID | None
    disconnect_event: bool
    timestamp: datetime


@dataclass(frozen=True)
class StageExecutionRecord:
    run_id: UUID
    lane_id: LaneID
    stage_key: StageKey
    status: ImplementationStatus
    started_at: datetime
    completed_at: datetime | None = None
    token_usage: int | None = None
    telemetry_refs: tuple[UUID, ...] = field(default_factory=tuple)
    residency_ledger_id: UUID | None = None



@dataclass(frozen=True)
class ImplementationBlueprintRecord:
    artifact_path: Path
    artifact_sha256: str
    target_repo_path: Path
    owner: ArtifactOwner
    status: ImplementationStatus
    evidence_refs: tuple[UUID, ...] = field(default_factory=tuple)
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    critical_path: bool = False
    stage_executions: tuple[StageExecutionRecord, ...] = field(default_factory=tuple)
