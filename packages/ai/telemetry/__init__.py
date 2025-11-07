from __future__ import annotations

# pyright: strict

"""Structured telemetry payloads for provider calls."""

from dataclasses import dataclass
from datetime import datetime, timezone

from ..types import AgentTask, ProviderCallMetrics
from ..types.identifiers import (
    CaseID,
    JobID,
    ModelName,
    OrganizationID,
    ProviderName,
    RouteName,
)


@dataclass(slots=True)
class ProviderCallRecord:
    """Metrics captured for a single provider call."""

    task: AgentTask
    provider: ProviderName
    model: ModelName
    route: RouteName | None
    metrics: ProviderCallMetrics
    cache_hit: bool = False


@dataclass(slots=True)
class TaskTelemetryEnvelope:
    """Telemetry payload persisted for auditing/analytics."""

    case_id: CaseID
    org_id: OrganizationID
    job_id: JobID | None
    call: ProviderCallRecord
    recorded_at: datetime

    @classmethod
    def now(
        cls,
        *,
        case_id: CaseID,
        org_id: OrganizationID,
        job_id: JobID | None,
        call: ProviderCallRecord,
    ) -> TaskTelemetryEnvelope:
        return cls(
            case_id=case_id,
            org_id=org_id,
            job_id=job_id,
            call=call,
            recorded_at=datetime.now(tz=timezone.utc),
        )


__all__ = ["ProviderCallRecord", "TaskTelemetryEnvelope"]
