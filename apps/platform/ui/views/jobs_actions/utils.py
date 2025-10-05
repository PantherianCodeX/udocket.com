from __future__ import annotations

# pyright: strict
import logging
from typing import Any, Protocol, cast
from uuid import UUID

from django.http import Http404, HttpRequest

from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.operations.tasks import transcribe_job

from ..common import JobRow, JobTelemetryPayload
from ..contexts import get_case_and_org
from ..presenters.jobs import friendly_job_title

log = logging.getLogger("apps.platform.ui")


class TaskWithDelay(Protocol):
    def delay(self, *args: Any, **kwargs: Any) -> Any:
        ...


class CaseArtifactLike(Protocol):
    id: UUID
    title: str
    metadata: Any

    def save(self, *args: Any, **kwargs: Any) -> None:
        ...


def resolve_job(case_id: str, job_id: UUID, request: HttpRequest) -> Job:
    case, _ = get_case_and_org(request, case_id)
    job = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case, pk=job_id)
        .first()
    )
    if not job:
        raise Http404
    return job


def resolve_case(case_id: str, request: HttpRequest) -> Case:
    case, _ = get_case_and_org(request, case_id)
    return case


def fallback_job_row(job: Job, telemetry: JobTelemetryPayload) -> JobRow:
    return {
        "job": job,
        "telemetry": telemetry,
        "title": friendly_job_title(job, telemetry),
        "children": [],
        "actions": [],
    }


def get_transcribe_job_task() -> TaskWithDelay:
    return cast(TaskWithDelay, transcribe_job)
