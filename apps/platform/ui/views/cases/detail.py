from __future__ import annotations

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false

from typing import Dict

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.platform.accounts.utils import resolve_request_organization
from apps.platform.cases.models import Case

from ..auth import ensure_authenticated
from ..contexts import compute_case_tool_state, get_case_and_org
from ..jobs import create_job
from .helpers import render_case_panel_with_refresh, resolve_panel, resolve_tool_key


@require_http_methods(["GET", "POST"])
def case_detail(request: HttpRequest, case_id: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    try:
        active_org = resolve_request_organization(request, required=True)
    except PermissionDenied:
        return redirect("ui-index")

    cases_qs = Case.objects.select_related("organization")
    case = cases_qs.for_user(getattr(request, "user", None)).filter(pk=case_id).first()
    if not case or case.organization_id != getattr(active_org, "id", None):
        raise Http404

    if request.method == "POST":
        response = create_job(request, case_id)
        if request.headers.get("HX-Request"):
            return response
        return redirect("ui-case-detail", case_id=case_id)

    state = compute_case_tool_state(request, case)
    tool_panels: Dict[str, Dict[str, object]] = state["tool_panels"]
    developer_cards = state["developer_cards"]
    case_header = state["case_header"]
    job_summary = state["job_summary"]
    latest_activity_ts = state["latest_activity_ts"]

    raw_tool = (request.GET.get("tool") or request.GET.get("module") or "")
    initial_tool_key = resolve_tool_key(raw_tool, tool_panels.keys(), default="intake")
    initial_panel = tool_panels.get(initial_tool_key)

    context = {
        "case": case,
        "job_summary": job_summary,
        "latest_activity_ts": latest_activity_ts,
        "case_header": case_header,
        "case_developer_cards": developer_cards,
        "initial_tool_key": initial_tool_key,
        "initial_tool_panel": initial_panel,
    }
    return render(request, "platform_ui/cases/detail.html", context)


@require_http_methods(["GET"])
def case_tool_panel(request: HttpRequest, case_id: str, tool_key: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)
    state = compute_case_tool_state(request, case)
    panels = state["tool_panels"]

    resolved_key, panel = resolve_panel(tool_key, panels, allow_fallback=False)
    if not resolved_key or not panel:
        raise Http404

    return render_case_panel_with_refresh(
        request,
        panel,
        case=case,
        state=state,
        active_tool=resolved_key,
        tools=[resolved_key],
    )
