from __future__ import annotations

from packages.ai.telemetry import ProviderCallRecord, TaskTelemetryEnvelope
from packages.ai.types import (
    AgentTask,
    CaseContext,
    ProviderCallMetrics,
)
from packages.ai.types.identifiers import CaseID, JobID, OrganizationID, ProviderName, ModelName, RouteName


def test_case_context_accepts_typed_ids() -> None:
    ctx = CaseContext(
        org_id=OrganizationID("org-1"),
        case_id=CaseID("case-1"),
        job_id=JobID("job-1"),
    )
    assert ctx.case_id == "case-1"


def test_provider_call_record_wraps_metrics() -> None:
    record = ProviderCallRecord(
        task=AgentTask.SUMMARIZE,
        provider=ProviderName("null-provider"),
        model=ModelName("null-model"),
        route=RouteName("route"),
        metrics=ProviderCallMetrics(total_tokens=10, prompt_tokens=6, completion_tokens=4, latency_ms=12.5),
    )
    envelope = TaskTelemetryEnvelope.now(
        case_id=CaseID("case-123"),
        org_id=OrganizationID("org-123"),
        job_id=JobID("job-123"),
        call=record,
    )
    assert envelope.call.metrics.total_tokens == 10
