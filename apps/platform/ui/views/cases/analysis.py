from __future__ import annotations

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false

from typing import Dict

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.platform.jobs.models import Job
from apps.platform.tenancy import scope_jobs

from ..auth import ensure_authenticated
from ..common import JobTelemetryPayload
from ..contexts import get_case_and_org
from ..presenters.cases import analysis_modules_context
from ..selectors import job_telemetry_map


@require_http_methods(["GET"])
def case_analysis_module(request: HttpRequest, case_id: str, agent: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)

    jobs_qs = (
        Job.objects.select_related("case", "case__organization", "reviewed_by")
        .filter(case=case)
        .order_by("-created_at")
    )
    jobs_scoped = scope_jobs(jobs_qs, getattr(request, "user", None))
    jobs_list = list(jobs_scoped)
    telemetry_map: Dict[str, JobTelemetryPayload] = job_telemetry_map(jobs_list, request)

    modules = analysis_modules_context(request, case, jobs_list, telemetry_map)
    module = next((item for item in modules if item.get("key") == agent), None)
    if not module:
        raise Http404

    return render(
        request,
        "platform_ui/components/cases/analysis_module.html",
        {"module": module, "case": case},
    )
