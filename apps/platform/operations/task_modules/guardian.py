# pyright: strict

from __future__ import annotations

import logging

from collections.abc import Sequence
from typing import cast

from celery import TaskProtocol, shared_task
from django.utils import timezone

from apps.platform.artifacts.models import CaseArtifact
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.operations.guardian import (
    build_guardian_context,
    build_guardian_review_record,
    snapshot_artifact_for_guardian,
    store_guardian_review,
)
from apps.platform.operations.runtime import (
    JobRuntimeContext,
    emit_job_update,
    safe_job_log,
    safe_job_meta,
)
from apps.platform.operations.utils import read_job_meta
from packages.udocket_core.agents.guardian_lib import GuardianVerdict
from packages.udocket_core.json_utils import JSONObject, coerce_json_object

log = logging.getLogger("apps.platform.operations.tasks.guardian")

@shared_task(bind=True)
def guardian_review_artifact(self: TaskProtocol, *, artifact_id: int) -> dict[str, object]:
    request_id = getattr(getattr(self, "request", None), "id", "") or ""
    try:
        artifact = CaseArtifact.typed_objects().select_related("case_fk").get(pk=artifact_id)
    except CaseArtifact.DoesNotExist:
        return {"status": "missing", "artifact_id": artifact_id}

    job_id = str(getattr(artifact, "job_id", "") or "")
    job_obj: Job | None = None
    if job_id:
        job_obj = Job.typed_objects().select_related("case").filter(pk=job_id).first()

    case_id_value = getattr(artifact, "case_id", None)
    case_id = str(case_id_value) if isinstance(case_id_value, str) and case_id_value else ""
    if not case_id and job_obj is not None:
        job_case = getattr(job_obj, "case", None)
        job_case_id = getattr(job_case, "id", None)
        if job_case_id is not None:
            case_id = str(job_case_id)
    if not case_id:
        artifact_case_fk = getattr(artifact, "case_fk", None)
        case_fk_id = getattr(artifact_case_fk, "id", None)
        if case_fk_id is not None:
            case_id = str(case_fk_id)
    org_value = getattr(artifact, "organization_id", None)
    if org_value is None and job_obj is not None:
        org_value = getattr(job_obj, "organization_id", None)
        if org_value is None:
            job_case = getattr(job_obj, "case", None)
            org_value = getattr(job_case, "organization_id", None)
    if org_value is None:
        artifact_case_fk = getattr(artifact, "case_fk", None)
        org_value = getattr(artifact_case_fk, "organization_id", None)
    org_id_str = str(org_value) if org_value else None

    context = build_guardian_context(org_id_str)

    task_meta: dict[str, object] = {
        "artifact_id": artifact.id,
        "artifact_type": artifact.type,
        "job_id": job_id or None,
        "case_id": case_id or None,
    }

    runtime: JobRuntimeContext | None = None
    if job_obj is not None:
        runtime = JobRuntimeContext(
            job=job_obj,
            case_id=case_id,
            org_id=org_id_str,
            task_name="guardian_review_artifact",
            task_id=request_id,
            task_meta=dict(task_meta),
        )
        runtime.transition(
            event="guardian.review.started",
            job_event_payload={
                "artifact_id": artifact.id,
                "guardian_status": "running",
            },
        )

    if context is None:
        review_record = coerce_json_object(
            {
                "status": "skipped",
                "reason": "guardian_not_configured",
                "reviewed_at": timezone.now().isoformat(),
                "artifact_id": int(artifact.id),
                "artifact_type": str(getattr(artifact, "type", "")),
            }
        )
        store_guardian_review(artifact, review_record)
        if runtime:
            runtime.transition(
                event="guardian.review.skipped",
                job_event_payload={
                    "artifact_id": artifact.id,
                    "guardian_status": "skipped",
                    "guardian_reason": "guardian_not_configured",
                },
            )
        return {"status": "skipped", "artifact_id": artifact.id, "reason": "guardian_not_configured"}

    artifact_payload = snapshot_artifact_for_guardian(artifact)
    if "content" not in artifact_payload and "parsed" not in artifact_payload:
        review_record = coerce_json_object(
            {
                "status": "skipped",
                "reason": "unreadable_artifact",
                "reviewed_at": timezone.now().isoformat(),
                "artifact_id": int(artifact.id),
                "artifact_type": str(getattr(artifact, "type", "")),
            }
        )
        store_guardian_review(artifact, review_record)
        if runtime:
            runtime.transition(
                event="guardian.review.skipped",
                job_event_payload={
                    "artifact_id": artifact.id,
                    "guardian_status": "skipped",
                    "guardian_reason": "unreadable_artifact",
                },
            )
        return {"status": "skipped", "artifact_id": artifact.id, "reason": "unreadable_artifact"}

    verdict: GuardianVerdict | None = None
    try:
        job_metadata: JSONObject = {}
        if job_id and org_id_str:
            try:
                job_metadata = coerce_json_object(read_job_meta(case_id, org_id_str, job_id))
            except Exception:
                job_metadata = {}

        artifact_type_upper = str(getattr(artifact, "type", "") or "").upper()
        applicable_instructions: list[JSONObject] = []
        for instruction in context.instructions:
            instruction_payload = dict(instruction)
            applies_to = instruction_payload.get("applies_to")
            if not applies_to:
                applicable_instructions.append(instruction_payload)
                continue
            if isinstance(applies_to, Sequence) and not isinstance(applies_to, (str, bytes, bytearray)):
                values = [
                    str(candidate).upper()
                    for candidate in cast(Sequence[object], applies_to)
                    if isinstance(candidate, str)
                ]
            else:
                values = []
            if artifact_type_upper in values:
                applicable_instructions.append(instruction_payload)

        case_data: JSONObject = {}
        case_obj: Case | None = getattr(artifact, "case_fk", None)
        if case_obj is None and case_id:
            case_obj = Case.typed_objects().filter(pk=case_id).first()
        if case_obj is not None:
            case_data = coerce_json_object(
                {
                    "id": str(getattr(case_obj, "id", "")),
                    "title": getattr(case_obj, "title", "") or "",
                    "client_name": getattr(case_obj, "client_name", "") or "",
                    "representation": getattr(case_obj, "representation", "") or "",
                }
            )

        artifact_meta_payload = coerce_json_object(getattr(artifact, "metadata", {}))
        guardian_context_payload: dict[str, object] = {
            "artifact_metadata": artifact_meta_payload,
            "job_metadata": job_metadata,
            "artifact_type": getattr(artifact, "type", None),
            "artifact_title": getattr(artifact, "title", None),
            "artifact_path": getattr(artifact, "path", None),
            "instructions": applicable_instructions,
            "all_instructions": context.instructions,
            "case": case_data,
        }

        review_options = {"temperature": context.temperature}
        verdict = context.agent.review(
            case_id=case_id,
            job_id=job_id,
            artifact_kind=getattr(artifact, "type", None) or "artifact",
            payload=artifact_payload,
            providers=context.provider_chain,
            model=context.model,
            options=review_options,
            provider_credentials=context.credentials,
            context=guardian_context_payload,
            max_tokens=context.max_tokens,
            temperature=context.temperature,
        )
    except Exception as exc:
        review_record = coerce_json_object(
            {
                "status": "error",
                "error": str(exc),
                "reviewed_at": timezone.now().isoformat(),
                "artifact_id": int(artifact.id),
                "artifact_type": str(getattr(artifact, "type", "")),
            }
        )
        store_guardian_review(artifact, review_record)
        if job_id:
            safe_job_log(case_id, org_id_str, job_id, f"Guardian review error: {exc}", level="ERROR")
        if runtime:
            runtime.transition(
                event="guardian.review.failed",
                job_event_payload={
                    "artifact_id": artifact.id,
                    "guardian_status": "error",
                    "guardian_error": str(exc),
                },
                meta_updates={"guardian_last_error": str(exc)},
            )
        raise

    status = "approved" if verdict.approved else "rejected"
    review_record = build_guardian_review_record(
        verdict=verdict,
        status=status,
        artifact=artifact,
        context=context,
        extra={
            "retry_attempts": context.agent.config.retry_attempts,
            "instructions_used": len(applicable_instructions),
        },
    )
    store_guardian_review(artifact, review_record)
    event_status = "SUCCEEDED" if verdict.approved else "FAILED"

    if job_id:
        reduced_record = dict(review_record)
        reduced_record.pop("artifact_id", None)
        reduced_record.pop("artifact_type", None)
        safe_job_meta(case_id, org_id_str, job_id, {"guardian_last_review": reduced_record})
        safe_job_log(
            case_id,
            org_id_str,
            job_id,
            "Guardian review completed" if verdict.approved else "Guardian review flagged violations",
        )
        emit_job_update(
            job_id,
            case_id=case_id,
            event="guardian.review.completed",
            status=event_status,
            payload={
                "guardian_status": status,
                "artifact_id": int(artifact.id),
            },
        )

    if runtime:
        runtime.transition(
            event="guardian.review.completed",
            job_event_payload={
                "artifact_id": artifact.id,
                "guardian_status": status,
            },
            meta_updates={"guardian_last_review": review_record},
        )

    return {
        "status": status,
        "artifact_id": artifact.id,
        "provider": verdict.provider,
        "model": verdict.model,
        "violations": verdict.violations,
        "remediation": verdict.remediation,
    }
