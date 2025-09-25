from __future__ import annotations

from typing import Iterable, Mapping, Tuple

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.tenancy import scope_jobs

from ..presenters.cases import case_progress_context
from ..selectors import job_telemetry_map


TOOL_KEY_ALIASES = {
    "": "case-details",
    "case": "case-details",
    "details": "case-details",
    "case-details": "case-details",
    "setup": "case-details",
    "intake": "case-details",
    "intake-form": "case-details",
    "transcribe": "transcribe",
    "transcription": "transcribe",
    "summary": "summary",
    "summaries": "summary",
    "timeline": "timeline",
}


def resolve_tool_key(
    raw_key: str,
    available_keys: Iterable[str],
    default: str = "case-details",
    allow_fallback: bool = True,
) -> str:
    """Resolve a tool key against aliases and available keys."""
    normalized = (raw_key or "").strip().lower()
    resolved = TOOL_KEY_ALIASES.get(normalized, normalized)
    available = set(available_keys)
    if resolved and resolved in available:
        return resolved
    if not allow_fallback:
        return ""
    if default in available:
        return default
    return next(iter(available), default)


def resolve_panel(
    raw_key: str,
    panels: Mapping[str, object],
    default: str = "case-details",
    allow_fallback: bool = True,
) -> Tuple[str, object | None]:
    """Return the canonical tool key and corresponding panel."""
    key = resolve_tool_key(raw_key, panels.keys(), default, allow_fallback=allow_fallback)
    return key, panels.get(key)


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
