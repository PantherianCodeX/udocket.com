from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.conf import settings
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
        CaseArtifact.scoped().for_user(user)
        .filter(organization=organization)
        .select_related("case_fk")
        .order_by("-created_at")
    )

    prefix = "artifacts"
    search_param = f"{prefix}_search"
    search_value = (request.GET.get(search_param) or "").strip()
    if search_value:
        queryset = queryset.filter(
            Q(title__icontains=search_value)
            | Q(type__icontains=search_value)
            | Q(case_fk__title__icontains=search_value)
            | Q(case_id__icontains=search_value)
            | Q(job_id__icontains=search_value)
        )

    raw_limit_choices = getattr(settings, "PLATFORM_UI_ARTIFACT_LIMIT_CHOICES", (10, 25, 50, 100, 200))
    limit_choices = sorted({int(value) for value in raw_limit_choices if int(value) > 0}) or [25, 50, 100, 200]
    default_limit = getattr(settings, "PLATFORM_UI_ARTIFACT_DEFAULT_LIMIT", limit_choices[0])
    page_size_param = f"{prefix}_page_size"
    try:
        page_size = int(request.GET.get(page_size_param, default_limit))
    except (TypeError, ValueError):
        page_size = default_limit
    if page_size not in limit_choices:
        for option in limit_choices:
            if page_size <= option:
                page_size = option
                break
        else:
            page_size = limit_choices[-1]

    page_param = f"{prefix}_page"
    try:
        page_number = int(request.GET.get(page_param, "1"))
    except (TypeError, ValueError):
        page_number = 1
    if page_number < 1:
        page_number = 1

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page_number)
    artifacts_list = list(page_obj.object_list)
    rows = _artifact_rows(artifacts_list)

    pagination = {
        "page": page_obj.number,
        "pages": paginator.num_pages or 1,
        "page_size": page_size,
        "total": paginator.count,
        "start": page_obj.start_index() if paginator.count else 0,
        "end": page_obj.end_index() if paginator.count else 0,
        "has_previous": page_obj.has_previous(),
        "has_next": page_obj.has_next(),
        "previous_page": page_obj.previous_page_number() if page_obj.has_previous() else 1,
        "next_page": page_obj.next_page_number() if page_obj.has_next() else paginator.num_pages or 1,
        "display_count": len(rows),
        "first_page": 1,
        "last_page": paginator.num_pages or 1,
    }

    type_counts = Counter(artifact.type for artifact in artifacts_list)

    filters = (
        {
            "type": "search",
            "id": "query",
            "param": search_param,
            "placeholder": "Filter artifacts",
            "value": search_value,
        },
    )

    filter_param_names = [search_param, page_param, page_size_param]
    filters_active = 1 if search_value else 0

    artifacts_table = {
        "id": "artifacts-table",
        "key": "artifacts",
        "title": "Artifacts",
        "pill": f"Page {pagination['page']} of {pagination['pages']}",
        "rows": rows,
        "columns": ARTIFACT_TABLE_COLUMNS,
        "column_ids": [col["id"] for col in ARTIFACT_TABLE_COLUMNS],
        "filters": filters,
        "row_template": "platform_ui/components/artifacts/_artifact_row.html",
        "empty_message": "No artifacts yet.",
        "show_identifiers": False,
        "allow_column_toggle": True,
        "pagination": pagination,
        "limit_value": page_size,
        "limit_options": limit_choices,
        "total_count": paginator.count,
        "param_prefix": prefix,
        "filter_param_names": filter_param_names,
        "filters_active": filters_active,
        "has_advanced_filters": False,
        "body_id": "artifacts-body",
    }

    section = {
        "pretitle": f"Artifacts · {organization.name}",
        "title": "Case artifacts",
        "subtitle": "Review generated transcripts, summaries, timelines, and related outputs across this organization.",
        "stats": [
            {
                "label": "Total artifacts",
                "value": paginator.count,
                "class": "border-white/10 bg-slate-900/70 text-white",
            },
            {
                "label": "Transcripts",
                "value": type_counts.get("TRANSCRIPT", 0),
                "class": "border-primary-400/40 bg-primary-500/10 text-primary-100",
            },
            {
                "label": "Analyses",
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
        "artifact_pagination": pagination,
    }

    return render(request, "platform_ui/artifacts/index.html", context)


__all__ = ["artifacts_index"]
