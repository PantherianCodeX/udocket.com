from __future__ import annotations

# pyright: strict
from typing import Any, Protocol

from celery import shared_task


class TaskProtocol(Protocol):
    request: Any


from apps.platform.jobs.models import Job
from apps.platform.operations.audit import emit as audit_emit
from apps.platform.operations.channels import send_case_update, send_job_update
from apps.platform.operations.runtime import JobRuntimeContext
from apps.platform.operations.services import execute_compose_job
from packages.udocket_core.agents import ComposeConfig


@shared_task(bind=True)
def compose_job(
    self: TaskProtocol,
    *_args: object,
    case_id: str,
    job_id: str,
    summary_job_id: str,
    llm_config_id: str | None = None,
    resume: bool = False,
) -> dict[str, object]:
    case_id = str(case_id)
    job_id = str(job_id)
    summary_job_id = str(summary_job_id)

    job = Job.typed_objects().select_related("case", "case__organization").get(pk=job_id)
    summary_job = (
        Job.typed_objects().select_related("case", "case__organization").get(pk=summary_job_id)
    )
    job_case = getattr(job, "case", None)
    summary_case = getattr(summary_job, "case", None)
    job_case_id = getattr(job_case, "id", None)
    summary_case_id = getattr(summary_case, "id", None)
    if job_case_id is None or summary_case_id is None or str(summary_case_id) != str(job_case_id):
        raise RuntimeError("Summary job belongs to a different case")

    compose_config = ComposeConfig.from_env()
    org_value = getattr(job, "organization_id", None)
    if org_value is None and job_case is not None:
        org_value = getattr(job_case, "organization_id", None)
    org_id = str(org_value) if org_value else None
    runtime = JobRuntimeContext(
        job=job,
        case_id=case_id,
        org_id=org_id,
        task_name="compose_job",
        task_id=getattr(self.request, "id", None) or "",
        task_meta={"summary_job_id": summary_job_id, "requested_llm_config_id": llm_config_id},
    )

    result = execute_compose_job(
        runtime=runtime,
        compose_config=compose_config,
        job=job,
        summary_job=summary_job,
        case_id=case_id,
        llm_config_id=llm_config_id,
        resume=resume,
    )

    send_job_update(
        str(job.id),
        event="job.succeeded",
        status=Job.Status.SUCCEEDED,
        case_id=case_id,
    )
    send_case_update(
        case_id,
        event="artifact.created",
        kind="compose",
        job_id=str(job.id),
    )
    audit_emit(
        None,
        case_id=case_id,
        event="analysis.compose.completed",
        data={"job_id": str(job.id), "summary_job_id": summary_job_id},
    )

    return result
