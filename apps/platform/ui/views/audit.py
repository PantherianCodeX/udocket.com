from __future__ import annotations

# pyright: strict
from typing import Any

from django.core.exceptions import PermissionDenied
from django.db import models
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.platform.accounts.utils import resolve_request_organization
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.jobs.models import Job, JobNote
from apps.platform.tenancy import scope_jobs

from .auth import ensure_authenticated
from .constants import DEFAULT_TABLE_FILTERS, GLOBAL_JOB_TABLE_COLUMNS
from .presenters.analysis_modules import artifact_payload
from .presenters.cases import table_config
from .presenters.guardian import (
    collect_guardian_reviews,
    guardian_stats_from_reviews,
    guardian_violation_entries,
)
from .presenters.jobs import build_job_rows
from .selectors import job_telemetry_map


def _organization_artifacts(request: HttpRequest, organization) -> list[dict[str, Any]]:
    user = getattr(request, "user", None)
    artifacts: list[dict[str, Any]] = []
    queryset = (
        CaseArtifact.scoped()
        .for_user(user)
        .filter(organization=organization)
        .exclude(type__iexact="AUDIO")
        .select_related("case_fk")
        .order_by("-created_at")
    )
    for artifact in queryset[:500]:
        payload = artifact_payload(artifact)
        payload["type"] = artifact.type
        case_obj = artifact.case_fk
        payload["case"] = {
            "id": str(case_obj.id) if case_obj else artifact.case_id,
            "title": getattr(case_obj, "title", ""),
        }
        artifacts.append(payload)
    return artifacts


def _guardian_dataset(
    request: HttpRequest, organization
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    artifacts = _organization_artifacts(request, organization)
    reviews = collect_guardian_reviews(artifacts)
    stats = guardian_stats_from_reviews(reviews)
    violations = guardian_violation_entries(reviews)
    return reviews, stats, violations


def _guardian_jobs(
    request: HttpRequest,
    organization,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    jobs_qs = Job.objects.select_related("case", "case__organization", "reviewed_by").filter(
        organization=organization
    )
    jobs_list = list(
        scope_jobs(jobs_qs.order_by("-created_at"), getattr(request, "user", None))[:200]
    )
    telemetry_map = job_telemetry_map(jobs_list, request)

    job_ids = [str(job.id) for job in jobs_list]
    transcript_artifacts: dict[str, CaseArtifact] = {}
    if job_ids:
        for art in CaseArtifact.objects.filter(job_id__in=job_ids, type="TRANSCRIPT").order_by(
            "-created_at"
        ):
            job_id_value = getattr(art, "job_id", None)
            if job_id_value and job_id_value not in transcript_artifacts:
                transcript_artifacts[job_id_value] = art

    note_counts: dict[str, int] = {}
    if jobs_list:
        note_rows = (
            JobNote.objects.filter(job__in=jobs_list)
            .values("job_id")
            .annotate(count=models.Count("id"))
        )
        note_counts = {str(row["job_id"]): int(row["count"]) for row in note_rows}

    display_rows, flat_rows = build_job_rows(
        jobs_list,
        telemetry_map,
        transcript_artifacts,
        note_counts=note_counts,
    )

    guardian_rows: list[dict[str, Any]] = []
    for row in flat_rows:
        if row.get("is_child"):
            continue
        metadata_payload = (row.get("telemetry") or {}).get("metadata") or {}
        if metadata_payload.get("guardian_last_review"):
            guardian_rows.append(row)

    return display_rows, guardian_rows, telemetry_map


@require_http_methods(["GET"])
def guardian_overview(request: HttpRequest) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    try:
        organization = resolve_request_organization(request, required=True)
    except PermissionDenied:
        raise Http404

    reviews, stats, violations = _guardian_dataset(request, organization)
    _, guardian_rows, _ = _guardian_jobs(request, organization)

    jobs_table = table_config(
        panel_key="guardian",
        title="Guardian Jobs",
        pill="Compliance",
        rows=guardian_rows,
        columns=GLOBAL_JOB_TABLE_COLUMNS,
        column_ids=[col["id"] for col in GLOBAL_JOB_TABLE_COLUMNS],
        filters=DEFAULT_TABLE_FILTERS,
        empty_message="No jobs with Guardian telemetry yet.",
        show_identifiers=False,
        case_id=None,
    )

    report_url = reverse("ui-guardian-report")

    section = {
        "pretitle": f"Guardian · {organization.name}",
        "title": "Guardian compliance",
        "subtitle": stats.get("status_detail")
        or "Monitor organization-wide Guardian activity, flagged violations, and review history.",
        "actions": [
            {
                "label": "View artifacts",
                "href": "/artifacts/",
                "variant": "default",
            },
            {
                "label": "Permissions catalog",
                "href": "/audit/permissions/",
                "variant": "default",
            },
        ],
        "stats": [
            {
                "label": "Total reviews",
                "value": stats.get("total_reviews", 0),
                "class": "border-white/10 bg-slate-900/70 text-white",
            },
            {
                "label": "Approved",
                "value": stats.get("approved", 0),
                "class": "border-emerald-400/40 bg-emerald-500/10 text-emerald-100",
            },
            {
                "label": "Flagged",
                "value": stats.get("rejected", 0),
                "class": "border-rose-400/40 bg-rose-500/10 text-rose-100",
            },
            {
                "label": "Violations",
                "value": stats.get("violation_count", 0),
                "class": "border-amber-400/40 bg-amber-500/10 text-amber-100",
            },
        ],
        "body_template": "platform_ui/audit/_guardian_overview.html",
        "body_context": {
            "organization": organization,
            "stats": stats,
            "reviews": reviews,
            "violations": violations,
            "violations_preview": violations[:5],
            "report_url": report_url,
        },
        "tables": [jobs_table],
    }

    context = {
        "section": section,
        "guardian_stats": stats,
        "guardian_violations": violations,
        "guardian_reviews": reviews,
    }

    return render(request, "platform_ui/audit/guardian.html", context)


@require_http_methods(["GET"])
def guardian_report(request: HttpRequest) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    try:
        organization = resolve_request_organization(request, required=True)
    except PermissionDenied:
        raise Http404

    reviews, stats, violations = _guardian_dataset(request, organization)
    payload = {
        "organization": {"id": str(organization.id), "name": organization.name},
        "generated_at": timezone.now().isoformat(),
        "stats": stats,
        "reviews": reviews,
        "violations": violations,
    }

    if request.GET.get("format") == "json":
        return JsonResponse(payload)

    context = {"report": payload}
    return render(request, "platform_ui/reports/guardian_org_report.html", context)


__all__ = ["guardian_overview", "guardian_report"]
