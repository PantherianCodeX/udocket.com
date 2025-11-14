"""Typed primitives for readiness planning artifacts.

This draft lives under specs until implementation promotes the models into the
real packages:
- packages/devops/readiness/domain.py (dataclasses + enums)
- packages/devops/readiness/service.py (ingest/refresh orchestration)
- packages/common/telemetry/vendor_usage.py (budget tracking structs)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Mapping, MutableSequence, NewType, Sequence
from uuid import UUID

StageKey = NewType("StageKey", str)
ComponentId = NewType("ComponentId", str)
PromptBundleId = NewType("PromptBundleId", str)
ExperimentId = NewType("ExperimentId", str)
DatasetHash = NewType("DatasetHash", str)
WorkspaceId = NewType("WorkspaceId", UUID)
ToolingDecisionId = NewType("ToolingDecisionId", UUID)
GapId = NewType("GapId", UUID)
SessionId = NewType("SessionId", UUID)


class StageStatus(StrEnum):
    COMPLETE = "complete"
    IN_FLIGHT = "in_flight"
    BLOCKED = "blocked"
    NOT_STARTED = "not_started"


class GapCategory(StrEnum):
    ARCHITECTURE = "architecture"
    TOOLING = "tooling"
    TELEMETRY = "telemetry"
    RESIDENCY = "residency"
    RISK = "risk"


class GapSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GapLifecycle(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    CLOSED = "closed"


class ValidationStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    VALIDATED = "validated"


class ToolingType(StrEnum):
    LANGSMITH = "langsmith"
    GUARDRAILS = "guardrails"
    PROMPT_REGISTRY = "prompt_registry"


class WorkspaceVendor(StrEnum):
    LANGSMITH = "LangSmith"
    LANGFUSE = "LangFuse"


class WorkspaceEnvironment(StrEnum):
    DEV = "dev"
    STAGING = "staging"
    PREPROD = "preprod"


class GovernanceState(StrEnum):
    APPROVED = "approved"
    PENDING = "pending"
    REVOKED = "revoked"


class ObservabilityEnvironment(StrEnum):
    DEV = "dev"
    STAGING = "staging"


class ObservabilityStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    SCHEDULED_FOR_DISABLE = "scheduled_for_disable"


class VendorName(StrEnum):
    LANGSMITH = "LangSmith"
    LANGFUSE = "LangFuse"


@dataclass(slots=True)
class MigrationStageReadiness:
    """Future home: packages/devops/readiness/domain.py."""

    stage_key: StageKey
    status: StageStatus
    owner_team: str
    last_validated_at: datetime | None
    evidence_links: Sequence[str]
    architecture_score: int
    compliance_score: int
    observability_score: int
    cutoff_date: date
    capability_gaps: MutableSequence["CapabilityGap"] = field(default_factory=list)


@dataclass(slots=True)
class CapabilityGap:
    """Future home: packages/devops/readiness/domain.py."""

    gap_id: GapId
    component_id: ComponentId
    stage_key: StageKey
    category: GapCategory
    severity: GapSeverity
    owner: str
    mitigation_plan: str
    due_date: date
    status: GapLifecycle
    resolution_notes: str | None = None
    related_controls: Sequence["ObservabilityControl"] = field(default_factory=tuple)


@dataclass(slots=True)
class ObservabilityControl:
    """Future home: packages/devops/readiness/observability.py."""

    control_id: UUID
    stage_key: StageKey
    metrics: Sequence[str]
    traces: Sequence[str] = field(default_factory=tuple)
    ops_jsonl_schema_version: str
    alert_routing: Sequence[str]
    langfuse_enabled: bool
    environment_scope: Sequence[ObservabilityEnvironment]
    enablement_evidence: Sequence[str]
    validation_status: ValidationStatus
    validation_timestamp: datetime | None


@dataclass(slots=True)
class LLMToolingDecision:
    """Future home: packages/devops/readiness/tooling.py."""

    decision_id: ToolingDecisionId
    tooling_type: ToolingType
    summary: str
    comparison_matrix: Sequence[str]
    approvals: Sequence[str]
    rollout_sequence: Sequence[str]
    residency_notes: str


@dataclass(slots=True)
class ToolingWorkspace:
    """Future home: packages/devops/readiness/tooling.py."""

    workspace_id: WorkspaceId
    vendor: WorkspaceVendor
    environment: WorkspaceEnvironment
    owners: Sequence[str]
    env_var_names: Sequence[str]
    expires_at: datetime
    governance_status: GovernanceState
    notes: str | None = None


@dataclass(slots=True)
class EvaluationEvidence:
    """Future home: packages/devops/readiness/evaluations.py."""

    experiment_id: ExperimentId
    dataset_hash: DatasetHash
    prompt_bundle_id: PromptBundleId
    metrics: Mapping[str, float]
    run_started_at: datetime
    run_completed_at: datetime
    owner: str
    governance_tags: Sequence[str]
    attachments: Sequence[str]


@dataclass(slots=True)
class ObservabilitySession:
    """Future home: packages/devops/readiness/observability.py."""

    session_id: SessionId
    environment: ObservabilityEnvironment
    sampling_rate: float
    status: ObservabilityStatus
    kill_switch_reference: str
    retention_days: int
    decommissioned_at: datetime | None


@dataclass(slots=True)
class VendorUsageBudget:
    """Future home: packages/common/telemetry/vendor_usage.py."""

    vendor: VendorName
    month: date
    allocated_amount_usd: Decimal
    actual_amount_usd: Decimal
    alert_80_sent_at: datetime | None = None
    alert_100_sent_at: datetime | None = None
    mitigation_plan: str | None = None

    @property
    def variance_percent(self) -> float:
        """(actual - allocated) / allocated * 100, guarded against division by zero."""

        if self.allocated_amount_usd == 0:
            raise ValueError("allocated_amount_usd cannot be zero")
        delta = self.actual_amount_usd - self.allocated_amount_usd
        return float(delta / self.allocated_amount_usd * 100)


FIELD_TARGETS: Mapping[str, str] = {
    "MigrationStageReadiness.stage_key": "packages/common/agents/stage_map.py",
    "MigrationStageReadiness.status": "packages/devops/readiness/domain.py",
    "MigrationStageReadiness.owner_team": "packages/devops/readiness/domain.py",
    "MigrationStageReadiness.last_validated_at": "packages/devops/readiness/domain.py",
    "MigrationStageReadiness.evidence_links": "packages/devops/readiness/domain.py",
    "MigrationStageReadiness.architecture_score": "packages/devops/readiness/domain.py",
    "MigrationStageReadiness.compliance_score": "packages/devops/readiness/domain.py",
    "MigrationStageReadiness.observability_score": "packages/devops/readiness/domain.py",
    "MigrationStageReadiness.cutoff_date": "packages/devops/readiness/domain.py",
    "MigrationStageReadiness.capability_gaps": "packages/devops/readiness/domain.py",
    "CapabilityGap.gap_id": "packages/devops/readiness/domain.py",
    "CapabilityGap.component_id": "packages/devops/readiness/domain.py",
    "CapabilityGap.stage_key": "packages/devops/readiness/domain.py",
    "CapabilityGap.category": "packages/devops/readiness/domain.py",
    "CapabilityGap.severity": "packages/devops/readiness/domain.py",
    "CapabilityGap.owner": "packages/devops/readiness/domain.py",
    "CapabilityGap.mitigation_plan": "packages/devops/readiness/domain.py",
    "CapabilityGap.due_date": "packages/devops/readiness/domain.py",
    "CapabilityGap.status": "packages/devops/readiness/domain.py",
    "CapabilityGap.resolution_notes": "packages/devops/readiness/domain.py",
    "CapabilityGap.related_controls": "packages/devops/readiness/observability.py",
    "ObservabilityControl.control_id": "packages/devops/readiness/observability.py",
    "ObservabilityControl.stage_key": "packages/devops/readiness/observability.py",
    "ObservabilityControl.metrics": "packages/devops/readiness/observability.py",
    "ObservabilityControl.traces": "packages/devops/readiness/observability.py",
    "ObservabilityControl.ops_jsonl_schema_version": "packages/devops/readiness/observability.py",
    "ObservabilityControl.alert_routing": "packages/devops/readiness/observability.py",
    "ObservabilityControl.langfuse_enabled": "packages/devops/readiness/observability.py",
    "ObservabilityControl.environment_scope": "packages/devops/readiness/observability.py",
    "ObservabilityControl.enablement_evidence": "packages/devops/readiness/observability.py",
    "ObservabilityControl.validation_status": "packages/devops/readiness/observability.py",
    "ObservabilityControl.validation_timestamp": "packages/devops/readiness/observability.py",
    "LLMToolingDecision.decision_id": "packages/devops/readiness/tooling.py",
    "LLMToolingDecision.tooling_type": "packages/devops/readiness/tooling.py",
    "LLMToolingDecision.summary": "packages/devops/readiness/tooling.py",
    "LLMToolingDecision.comparison_matrix": "packages/devops/readiness/tooling.py",
    "LLMToolingDecision.approvals": "packages/devops/readiness/tooling.py",
    "LLMToolingDecision.rollout_sequence": "packages/devops/readiness/tooling.py",
    "LLMToolingDecision.residency_notes": "packages/devops/readiness/tooling.py",
    "ToolingWorkspace.workspace_id": "packages/devops/readiness/tooling.py",
    "ToolingWorkspace.vendor": "packages/devops/readiness/tooling.py",
    "ToolingWorkspace.environment": "packages/devops/readiness/tooling.py",
    "ToolingWorkspace.owners": "packages/devops/readiness/tooling.py",
    "ToolingWorkspace.env_var_names": "packages/devops/readiness/tooling.py",
    "ToolingWorkspace.expires_at": "packages/devops/readiness/tooling.py",
    "ToolingWorkspace.governance_status": "packages/devops/readiness/tooling.py",
    "ToolingWorkspace.notes": "packages/devops/readiness/tooling.py",
    "EvaluationEvidence.experiment_id": "packages/devops/readiness/evaluations.py",
    "EvaluationEvidence.dataset_hash": "packages/devops/readiness/evaluations.py",
    "EvaluationEvidence.prompt_bundle_id": "packages/devops/readiness/evaluations.py",
    "EvaluationEvidence.metrics": "packages/devops/readiness/evaluations.py",
    "EvaluationEvidence.run_started_at": "packages/devops/readiness/evaluations.py",
    "EvaluationEvidence.run_completed_at": "packages/devops/readiness/evaluations.py",
    "EvaluationEvidence.owner": "packages/devops/readiness/evaluations.py",
    "EvaluationEvidence.governance_tags": "packages/devops/readiness/evaluations.py",
    "EvaluationEvidence.attachments": "packages/devops/readiness/evaluations.py",
    "ObservabilitySession.session_id": "packages/devops/readiness/observability.py",
    "ObservabilitySession.environment": "packages/devops/readiness/observability.py",
    "ObservabilitySession.sampling_rate": "packages/devops/readiness/observability.py",
    "ObservabilitySession.status": "packages/devops/readiness/observability.py",
    "ObservabilitySession.kill_switch_reference": "packages/devops/readiness/observability.py",
    "ObservabilitySession.retention_days": "packages/devops/readiness/observability.py",
    "ObservabilitySession.decommissioned_at": "packages/devops/readiness/observability.py",
    "VendorUsageBudget.vendor": "packages/common/telemetry/vendor_usage.py",
    "VendorUsageBudget.month": "packages/common/telemetry/vendor_usage.py",
    "VendorUsageBudget.allocated_amount_usd": "packages/common/telemetry/vendor_usage.py",
    "VendorUsageBudget.actual_amount_usd": "packages/common/telemetry/vendor_usage.py",
    "VendorUsageBudget.alert_80_sent_at": "packages/common/telemetry/vendor_usage.py",
    "VendorUsageBudget.alert_100_sent_at": "packages/common/telemetry/vendor_usage.py",
    "VendorUsageBudget.mitigation_plan": "packages/common/telemetry/vendor_usage.py",
}

__all__ = [
    "CapabilityGap",
    "ComponentId",
    "DatasetHash",
    "EvaluationEvidence",
    "FIELD_TARGETS",
    "GapCategory",
    "GapId",
    "GapLifecycle",
    "GapSeverity",
    "GovernanceState",
    "LLMToolingDecision",
    "MigrationStageReadiness",
    "ObservabilityControl",
    "ObservabilityEnvironment",
    "ObservabilitySession",
    "ObservabilityStatus",
    "PromptBundleId",
    "StageKey",
    "StageStatus",
    "ToolingDecisionId",
    "ToolingType",
    "ToolingWorkspace",
    "ValidationStatus",
    "VendorName",
    "VendorUsageBudget",
    "WorkspaceEnvironment",
    "WorkspaceId",
    "WorkspaceVendor",
]
