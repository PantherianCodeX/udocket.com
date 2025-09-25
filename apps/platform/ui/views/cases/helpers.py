from __future__ import annotations

from typing import Iterable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.tenancy import scope_jobs

from ..presenters.cases import case_progress_context
from ..selectors import job_telemetry_map


def case_progress_response(request: HttpRequest, case: Case) -> HttpResponse:
    """Render the case progress partial with up-to-date job context."""
    jobs_qs = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case)
        .order_by("-created_at")
    )
    jobs_list: Iterable[Job] = scope_jobs(jobs_qs, getattr(request, "user", None))
    jobs_sequence = list(jobs_list)
    telemetry_map = job_telemetry_map(jobs_sequence, request)
    context = {"case": case, **case_progress_context(case, jobs_sequence, telemetry_map)}
    return render(request, "platform_ui/partials/case_progress.html", context)
