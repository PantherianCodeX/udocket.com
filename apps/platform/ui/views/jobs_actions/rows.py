from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.platform.jobs.models import Job

from ..auth import ensure_authenticated
from ..common import JobRow
from ..constants import CASE_JOB_TABLE_COLUMNS
from ..contexts import user_can_review_case
from ..presenters.job_actions import build_job_action_entries
from ..presenters.jobs import build_job_rows
from ..selectors import job_telemetry_payload
from .utils import fallback_job_row, resolve_case


@require_http_methods(["GET"])
def case_job_row(request: HttpRequest, case_id: str, job_id: UUID) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case = resolve_case(case_id, request)
    job = (
        Job.objects.select_related("case", "case__organization").filter(case=case, pk=job_id).first()
    )
    if not job:
        raise Http404

    telemetry_dict = job_telemetry_payload(job, request, ui_mode=True)
    telemetry_map: Dict[str, Any] = {str(job.id): telemetry_dict}
    _, flat_rows = build_job_rows([job], telemetry_map)
    if not flat_rows:
        fallback = fallback_job_row(job, telemetry_dict)
        fallback["actions"] = build_job_action_entries(
            job,
            telemetry_dict,
            can_review=user_can_review_case(getattr(request, "user", None), job.case),
            is_child=False,
        )
        return render(
            request,
            "platform_ui/partials/job_row.html",
            {
                "row": fallback,
                "table_columns": CASE_JOB_TABLE_COLUMNS,
            },
        )

    row: JobRow = flat_rows[0]
    row["actions"] = build_job_action_entries(
        job,
        telemetry_dict,
        can_review=user_can_review_case(getattr(request, "user", None), job.case),
        is_child=False,
    )
    return render(
        request,
        "platform_ui/partials/job_row.html",
        {
            "row": row,
            "table_columns": CASE_JOB_TABLE_COLUMNS,
        },
    )
