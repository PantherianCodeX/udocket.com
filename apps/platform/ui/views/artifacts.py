from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.platform.accounts.utils import resolve_request_organization
from apps.platform.artifacts.models import CaseArtifact

from .auth import ensure_authenticated
from .constants import ARTIFACT_TABLE_COLUMNS
from .presenters.analysis_modules import artifact_payload


def _artifact_rows(artifacts: List[CaseArtifact]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for artifact in artifacts:
        payload = artifact_payload(artifact)
        case_obj = artifact.case_fk
        case_id = str(case_obj.id) if case_obj else artifact.case_id
        case_title = getattr(case_obj, "title", "") if case_obj else ""
        source = payload.get("source") or "—"
        created_at = artifact.created_at
        rows.append(
            {
                "id": artifact.pk,
                "title": payload.get("title") or payload.get("filename") or "Artifact",
                "type": artifact.type,
                "case": {"id": case_id, "title": case_title},
                "created": created_at,
                "source": source,
                "download_url": payload.get("download_url"),
                "metadata": payload.get("metadata") or {},
                "filter": " ".join(
                    filter(
                        None,
                        [
                            payload.get("title"),
                            payload.get("filename"),
                            artifact.type,
                            case_title,
                            case_id,
                            source,
                        ],
                    )
                ).lower(),
            }
        )
    return rows


@require_http_methods(["GET"])
def artifacts_index(request: HttpRequest) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    try:
        organization = resolve_request_organization(request, required=True)
    except PermissionDenied:
        raise Http404

    user = getattr(request, "user", None)
    queryset = (
        CaseArtifact.objects.for_user(user)
        .filter(organization=organization)
        .select_related("case_fk")
        .order_by("-created_at")
    )
    artifacts_list = list(queryset[:200])
    rows = _artifact_rows(artifacts_list)

    type_counts = Counter(artifact.type for artifact in artifacts_list)

    filters = (
        {
            "type": "search",
            "id": "query",
            "placeholder": "Filter artifacts",
        },
    )

    artifacts_table = {
        "id": "artifacts-table",
        "key": "artifacts",
        "title": "Artifacts",
        "pill": "Latest 200",
        "rows": rows,
        "columns": ARTIFACT_TABLE_COLUMNS,
        "column_ids": [col["id"] for col in ARTIFACT_TABLE_COLUMNS],
        "filters": filters,
        "row_template": "platform_ui/components/artifacts/_artifact_row.html",
        "empty_message": "No artifacts yet.",
        "show_identifiers": False,
        "allow_column_toggle": True,
    }

    section = {
        "pretitle": f"Artifacts · {organization.name}",
        "title": "Case artifacts",
        "subtitle": "Review generated transcripts, summaries, timelines, and related outputs across this organization.",
        "stats": [
            {
                "label": "Total artifacts",
                "value": len(artifacts_list),
                "class": "border-white/10 bg-slate-900/70 text-white",
            },
            {
                "label": "Transcripts",
                "value": type_counts.get("TRANSCRIPT", 0),
                "class": "border-primary-400/40 bg-primary-500/10 text-primary-100",
            },
            {
                "label": "Summaries",
                "value": type_counts.get("SUMMARY", 0),
                "class": "border-emerald-400/40 bg-emerald-500/10 text-emerald-100",
            },
            {
                "label": "Timelines",
                "value": type_counts.get("TIMELINE", 0),
                "class": "border-amber-400/40 bg-amber-500/10 text-amber-100",
            },
        ],
        "tables": [artifacts_table],
    }

    context = {
        "section": section,
        "artifact_rows": rows,
        "artifact_type_counts": type_counts,
    }

    return render(request, "platform_ui/artifacts/index.html", context)


__all__ = ["artifacts_index"]
