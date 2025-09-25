from __future__ import annotations

import logging
from uuid import UUID
from typing import Dict, Optional, cast

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.platform.accounts.utils import resolve_request_organization
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.tenancy import scope_jobs

from .auth import ensure_authenticated
from .contexts import get_case_and_org, job_detail_context, user_can_review_case
from .constants import DEFAULT_TABLE_FILTERS, GLOBAL_JOB_TABLE_COLUMNS
from .presenters.cases import table_config
from .presenters.job_actions import build_job_action_entries
from .presenters.jobs import build_job_rows
from .selectors import job_telemetry_map

# Backwards-compatible exports for tests and legacy imports
from .jobs_actions import create_job as create_job
from .jobs_actions import transcribe_job_task as transcribe_job_task

__all__ = [
    "jobs",
    "job_detail_panel",
    "case_job_detail_panel",
    "create_job",
    "transcribe_job_task",
]

log = logging.getLogger("apps.platform.ui")


@require_http_methods(["GET"])
def jobs(request: HttpRequest) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    try:
        organization = resolve_request_organization(request, required=True)
    except PermissionDenied:
        raise Http404

    jobs_qs = Job.objects.select_related("case", "case__organization", "reviewed_by")
    scoped = scope_jobs(jobs_qs, getattr(request, "user", None))
    scoped = scoped.filter(organization=organization)
    jobs_list = list(scoped[:200])

    telemetry_map = job_telemetry_map(jobs_list, request)

    job_ids = [str(job.id) for job in jobs_list]
    transcript_artifacts: Dict[str, CaseArtifact] = {}
    if job_ids:
        for art in (
            CaseArtifact.objects.filter(job_id__in=job_ids, type="TRANSCRIPT")
            .order_by("-created_at")
        ):
            job_id_value = cast(Optional[str], getattr(art, "job_id", None))
            if job_id_value and job_id_value not in transcript_artifacts:
                transcript_artifacts[job_id_value] = art

    display_rows, flat_rows = build_job_rows(jobs_list, telemetry_map, transcript_artifacts)

    user = getattr(request, "user", None)
    for row in flat_rows:
        job_obj: Optional[Job] = row.get("job")
        can_review = False
        case_obj: Optional[Case] = None
        if job_obj:
            case_obj = getattr(job_obj, "case", None)
            if isinstance(case_obj, Case):
                can_review = user_can_review_case(user, case_obj)
        row["actions"] = build_job_action_entries(
            job_obj,
            row.get("telemetry"),
            can_review=can_review,
            is_child=bool(row.get("is_child")),
        )
        if case_obj:
            display_meta = row.setdefault("display", {})
            display_meta["case"] = {
                "title": case_obj.title,
                "id": str(case_obj.id),
            }

    context = {
        "active_org": organization,
        "job_rows": display_rows,
        "job_columns": list(GLOBAL_JOB_TABLE_COLUMNS),
        "job_column_ids": [col["id"] for col in GLOBAL_JOB_TABLE_COLUMNS],
        "job_filters": DEFAULT_TABLE_FILTERS,
        "job_total": len(display_rows),
        "job_show_identifiers": False,
        "jobs_table": table_config(
            panel_key="jobs",
            title="Jobs",
            pill="Live updates",
            rows=display_rows,
            columns=GLOBAL_JOB_TABLE_COLUMNS,
            column_ids=[col["id"] for col in GLOBAL_JOB_TABLE_COLUMNS],
            filters=DEFAULT_TABLE_FILTERS,
            empty_message="No jobs yet.",
            show_identifiers=False,
            case_id=None,
        ),
    }
    return render(request, "platform_ui/jobs/index.html", context)


@require_http_methods(["GET"])
def job_detail_panel(request: HttpRequest, job_id: UUID) -> HttpResponse:
    try:
        auth_response = ensure_authenticated(request)
        if auth_response:
            return auth_response

        jobs_qs = Job.objects.select_related("case", "case__organization", "reviewed_by").filter(pk=job_id)
        job = scope_jobs(jobs_qs, getattr(request, "user", None)).first()
        if not job:
            raise Http404

        title_edit = str(request.GET.get("title_edit") or "").lower() in {"1", "true", "yes", "on"}
        context = job_detail_context(request, job, title_edit=title_edit)
        template = (
            "platform_ui/components/jobs/job_detail_audio_conversion.html"
            if context.get("job_kind", "").lower() == "audio_conversion"
            else "platform_ui/components/jobs/job_detail.html"
        )
        return render(request, template, context)
    except Http404:
        raise
    except Exception as exc:  # noqa: BLE001
        log.exception("job_detail_panel error", extra={"job_id": job_id})
        return HttpResponse(
            '<div class="space-y-2 text-xs text-rose-200">'
            "<p>Unable to load job detail.</p>"
            f"<p class=\"font-mono text-[10px] text-rose-300\">{exc}</p>"
            "</div>",
            status=500,
        )


@require_http_methods(["GET"])
def case_job_detail_panel(request: HttpRequest, case_id: str, job_id: UUID) -> HttpResponse:
    try:
        auth_response = ensure_authenticated(request)
        if auth_response:
            return auth_response

        case, _ = get_case_and_org(request, case_id)
        job = (
            Job.objects.select_related("case", "case__organization", "reviewed_by")
            .filter(case=case, pk=job_id)
            .first()
        )
        if not job:
            raise Http404

        title_edit = str(request.GET.get("title_edit") or "").lower() in {"1", "true", "yes", "on"}
        context = job_detail_context(request, job, title_edit=title_edit)
        context["case"] = case
        template = (
            "platform_ui/components/jobs/job_detail_audio_conversion.html"
            if context.get("job_kind", "").lower() == "audio_conversion"
            else "platform_ui/components/jobs/job_detail.html"
        )
        return render(request, template, context)
    except Http404:
        raise
    except Exception as exc:  # noqa: BLE001
        log.exception(
            "case_job_detail_panel error", extra={"job_id": job_id, "case_id": case_id}
        )
        return HttpResponse(
            '<div class="space-y-2 text-xs text-rose-200">'
            "<p>Unable to load job detail.</p>"
            f"<p class=\"font-mono text-[10px] text-rose-300\">{exc}</p>"
            "</div>",
            status=500,
        )
