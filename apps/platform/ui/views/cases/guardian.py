from __future__ import annotations

# pyright: strict
from typing import Dict

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from apps.platform.artifacts.models import CaseArtifact

from ..auth import ensure_authenticated
from ..contexts import get_case_and_org
from ..presenters.guardian import (
    collect_guardian_reviews,
    guardian_report_payload,
    guardian_stats_from_reviews,
    guardian_violation_entries,
)


@require_http_methods(["GET"])
def case_guardian_report(request: HttpRequest, case_id: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)

    artifacts: list[Dict[str, object]] = []
    for artifact in CaseArtifact.objects.filter(case_id=str(case.id)).order_by("-created_at"):
        metadata = artifact.metadata or {}
        if not metadata.get("guardian_history"):
            continue
        artifacts.append(
            {
                "id": artifact.id,
                "title": artifact.title or artifact.path or f"Artifact {artifact.id}",
                "type": artifact.type,
                "metadata": metadata,
                "created_at": artifact.created_at,
            }
        )

    guardian_reviews = collect_guardian_reviews(artifacts)
    guardian_stats = guardian_stats_from_reviews(guardian_reviews)
    guardian_violations = guardian_violation_entries(guardian_reviews)
    payload = guardian_report_payload(
        case=case,
        stats=guardian_stats,
        reviews=guardian_reviews,
        violations=guardian_violations,
    )

    if request.GET.get("format") == "json":
        return JsonResponse(payload)

    context = {
        "case": case,
        "report": payload,
        "generated_at": timezone.now(),
    }
    response = render(request, "platform_ui/reports/guardian_case_report.html", context)
    filename = f"guardian-report-{case.id}.html"
    response["Content-Disposition"] = f"inline; filename={filename}"
    return response


__all__ = ["case_guardian_report"]
