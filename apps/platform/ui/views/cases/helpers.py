from __future__ import annotations
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Tuple, cast

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string

from apps.platform.authorization.capabilities import has_capability
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.tenancy import scope_jobs

from ..presenters.cases import case_progress_context, collect_case_artifacts
from ..selectors import job_telemetry_map
from packages.udocket_common.json_utils import stringify_json


TOOL_KEY_ALIASES = {
    "": "intake",
    "case": "intake",
    "details": "intake",
    "case-details": "intake",
    "setup": "intake",
    "intake": "intake",
    "intake-form": "intake",
    "transcribe": "transcribe",
    "transcription": "transcribe",
    "summary": "analyze",
    "summaries": "analyze",
    "timeline": "timeline",
}


def check_case_update_permission(request: HttpRequest, case: Case) -> HttpResponse | None:
    """Return a forbidden response when the requester cannot update the case."""
    dev_open = getattr(settings, "PLATFORM_DEV_OPEN", False)
    user = getattr(request, "user", None)
    if dev_open:
        return None
    if user and getattr(user, "is_authenticated", False) and has_capability(user, str(case.id), "case.update"):
        return None
    return HttpResponse("Forbidden", status=403)


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
    artifacts = collect_case_artifacts(request, case)
    context = {
        "case": case,
        **case_progress_context(
            case,
            jobs_sequence,
            telemetry_map,
        ),
    }
    return render(request, "platform_ui/components/cases/case_progress.html", context)


def resolve_tool_key(
    raw_key: str,
    available_keys: Iterable[str],
    default: str = "intake",
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
    default: str = "intake",
    allow_fallback: bool = True,
) -> Tuple[str, object | None]:
    """Return the canonical tool key and corresponding panel."""
    key = resolve_tool_key(raw_key, panels.keys(), default, allow_fallback=allow_fallback)
    return key, panels.get(key)


def case_refresh_trigger(
    case: Case,
    state: Mapping[str, object],
    *,
    active_tool: str,
    tools: Iterable[str] | None = None,
) -> Dict[str, object]:
    tools_list = list(tools) if tools is not None else [active_tool]
    tool_panels = state.get("tool_panels") if isinstance(state, Mapping) else {}
    active_panel = {}
    if isinstance(tool_panels, Mapping):
        active_panel = tool_panels.get(active_tool, {})
    return {
        "tools": tools_list,
        "active_tool": active_tool,
        "header_html": render_to_string(
            "platform_ui/tools/_case_header.html",
            {"case": case, "case_header": state.get("case_header")},
        ),
        "cards_html": render_to_string(
            "platform_ui/tools/_developer_cards.html",
            {
                "case": case,
                "cards": state.get("developer_cards"),
                "active_tool": active_tool,
            },
        ),
        "collaboration_html": render_to_string(
            "platform_ui/components/cases/_collaboration_panel.html",
            {"panel": active_panel},
        ),
    }


def render_case_panel_with_refresh(
    request: HttpRequest,
    panel: object,
    *,
    case: Case,
    state: Mapping[str, object],
    active_tool: str,
    tools: Iterable[str] | None = None,
    extra_triggers: MutableMapping[str, object] | None = None,
    status: int = 200,
) -> HttpResponse:
    """Render a panel and attach refreshed case trigger payload."""
    refresh_payload = case_refresh_trigger(
        case,
        state,
        active_tool=active_tool,
        tools=tools,
    )
    snippets = {
        "header_html": refresh_payload.get("header_html"),
        "cards_html": refresh_payload.get("cards_html"),
        "collaboration_html": refresh_payload.get("collaboration_html"),
    }
    context = {
        "panel": panel,
        "case_refresh": snippets,
    }
    response = render(request, "platform_ui/tools/_panel.html", context, status=status)
    trigger_payload: Dict[str, object] = dict(extra_triggers or {})
    trigger_payload["case-view-refreshed"] = {
        "tools": refresh_payload.get("tools", []),
        "active_tool": refresh_payload.get("active_tool"),
    }
    # Set HTMX trigger header (typing-safe cast for stubs)
    cast(Any, response)["HX-Trigger"] = stringify_json(trigger_payload)
    return response
