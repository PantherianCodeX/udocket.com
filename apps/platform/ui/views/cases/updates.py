from __future__ import annotations

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false

from datetime import datetime
import json
from typing import Any, Dict, List

from django.http import HttpRequest, HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from ..auth import ensure_authenticated
from ..contexts import compute_case_tool_state, get_case_and_org
from ..presenters.cases import case_field_specs
from .helpers import check_case_update_permission, render_case_panel_with_refresh
from .membership import reconcile_case_memberships
from apps.platform.operations.llm import get_org_llm_overrides, set_org_llm_overrides


LLM_STAGE_GROUPS: Dict[str, List[str]] = {
    "summary": [
        "summarize.context_builder",
        "summarize.extract_outline",
        "summarize.build_timeline_seeds",
        "summarize.build_entity_hints",
        "summarize.draft_markdown",
        "summarize.qa_and_finalize",
    ],
    "timeline": ["timeline.builder"],
    "graph": ["graph.extractor"],
}


@require_http_methods(["POST"])
def case_update_title(request: HttpRequest, case_id: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)
    new_title = (request.POST.get("title") or "").strip()
    if not new_title:
        new_title = case.title or case.id
    if new_title != case.title:
        case.title = new_title
        case.save(update_fields=["title"])
    return render(request, "platform_ui/components/cases/case_title.html", {"case": case})


@require_http_methods(["POST"])
def case_details_update(request: HttpRequest, case_id: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)

    permission_denied = check_case_update_permission(request, case)
    if permission_denied:
        return permission_denied

    form_errors: Dict[str, str] = {}
    case_updates: Dict[str, Any] = {}
    specs = case_field_specs()

    for spec in specs:
        name = spec["name"]
        field_type = spec.get("type", "text")
        raw_value = request.POST.get(name)

        if field_type in {"text", "textarea", "choice"}:
            case_updates[name] = raw_value or ""
            continue

        if field_type == "datetime":
            if raw_value:
                try:
                    dt = datetime.strptime(raw_value, "%Y-%m-%dT%H:%M")
                    aware = timezone.make_aware(dt, timezone.get_current_timezone())
                    case_updates[name] = aware
                except Exception:
                    form_errors[name] = "Enter a valid date and time."
            else:
                case_updates[name] = None
            continue

        if field_type == "date":
            if raw_value:
                try:
                    case_updates[name] = datetime.strptime(raw_value, "%Y-%m-%d").date()
                except Exception:
                    form_errors[name] = "Enter a valid date."
            else:
                case_updates[name] = None
            continue

    reviewer_id = (request.POST.get("reviewer_id") or "").strip()
    client_user_id = (request.POST.get("client_user_id") or "").strip()
    owner_id = (request.POST.get("owner_id") or "").strip()
    contributor_ids = set((request.POST.getlist("contributor_ids") or []) if hasattr(request, "POST") else [])
    representation_value = (request.POST.get("representation") or "").strip()
    engagement_value = (request.POST.get("engagement_model") or "standard").strip().lower()

    if form_errors:
        state = compute_case_tool_state(request, case)
        panel = state["tool_panels"].get("case-details")
        if panel:
            panel_body = panel.get("body_context", {})
            panel_body["form_errors"] = form_errors
        return render(request, "platform_ui/tools/_panel.html", {"panel": panel}, status=400)

    update_fields: List[str] = []
    for field_name, value in case_updates.items():
        if hasattr(case, field_name) and getattr(case, field_name) != value:
            setattr(case, field_name, value)
            update_fields.append(field_name)

    if representation_value and representation_value != case.representation:
        case.representation = representation_value
        update_fields.append("representation")

    if engagement_value == "legal_aid":
        if not case.legal_aid:
            case.legal_aid = True
            update_fields.append("legal_aid")
        if case.pro_bono:
            case.pro_bono = False
            update_fields.append("pro_bono")
    elif engagement_value == "pro_bono":
        if not case.pro_bono:
            case.pro_bono = True
            update_fields.append("pro_bono")
        if case.legal_aid:
            case.legal_aid = False
            update_fields.append("legal_aid")
    else:
        if case.legal_aid:
            case.legal_aid = False
            update_fields.append("legal_aid")
        if case.pro_bono:
            case.pro_bono = False
            update_fields.append("pro_bono")

    update_fields.extend(
        reconcile_case_memberships(
            case,
            reviewer_id=reviewer_id,
            client_user_id=client_user_id,
            owner_id=owner_id,
            contributor_ids=contributor_ids,
        )
    )

    if update_fields:
        case.save(update_fields=list(set(update_fields)))

    state = compute_case_tool_state(request, case)
    panel = state["tool_panels"].get("case-details")
    if panel is None:
        return render(request, "platform_ui/tools/_panel.html", {"panel": panel})
    return render_case_panel_with_refresh(
        request,
        panel,
        case=case,
        state=state,
        active_tool="case-details",
        tools=["case-details"],
    )


@require_http_methods(["POST"])
def case_llm_settings(request: HttpRequest, case_id: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)

    permission_denied = check_case_update_permission(request, case)
    if permission_denied:
        return permission_denied

    organization_id = getattr(case, "organization_id", None)
    if not organization_id:
        return HttpResponseBadRequest("Case is not associated with an organization.")

    try:
        raw_body = request.body.decode("utf-8") if request.body else "{}"
        payload = json.loads(raw_body or "{}")
    except Exception:  # noqa: BLE001
        return HttpResponseBadRequest("Invalid JSON payload.")

    if not isinstance(payload, dict):
        return HttpResponseBadRequest("Invalid JSON payload.")

    target_raw = payload.get("target")
    if not isinstance(target_raw, str) or not target_raw.strip():
        return HttpResponseBadRequest("Missing LLM target.")
    target = target_raw.strip().lower()
    if target not in LLM_STAGE_GROUPS:
        return HttpResponseBadRequest("Unknown LLM target.")

    incoming_overrides = payload.get("overrides")
    if not isinstance(incoming_overrides, dict):
        incoming_overrides = {}

    cleaned_overrides: Dict[str, Dict[str, Any]] = {}
    stage_keys = LLM_STAGE_GROUPS[target]
    for stage_key in stage_keys:
        stage_payload = incoming_overrides.get(stage_key)
        if not isinstance(stage_payload, dict):
            continue
        provider_str = stage_payload.get("provider")
        provider = str(provider_str or "").strip().lower()
        if not provider:
            continue
        fallbacks_raw = stage_payload.get("fallbacks")
        fallbacks: List[str] = []
        if isinstance(fallbacks_raw, list):
            for item in fallbacks_raw:
                if isinstance(item, str):
                    value = item.strip().lower()
                    if value and value not in fallbacks:
                        fallbacks.append(value)
        model_value = stage_payload.get("model")
        model = str(model_value or "").strip()
        allow_offline = bool(stage_payload.get("allow_offline_fallback"))
        cleaned_overrides[stage_key] = {
            "provider": provider,
            "model": model,
            "fallbacks": fallbacks,
            "allow_offline_fallback": allow_offline,
        }

    existing = get_org_llm_overrides(str(organization_id))
    updated: Dict[str, Dict[str, Any]] = dict(existing)
    for stage_key in stage_keys:
        if stage_key in cleaned_overrides:
            updated[stage_key] = cleaned_overrides[stage_key]
        else:
            updated.pop(stage_key, None)

    set_org_llm_overrides(organization_id=str(organization_id), overrides=updated)

    response_overrides = {key: updated[key] for key in stage_keys if key in updated}

    raw_chain = payload.get("provider_chain")
    provider_chain: List[str] = []
    if isinstance(raw_chain, list):
        for item in raw_chain:
            if isinstance(item, str):
                name = item.strip().lower()
                if name and name not in provider_chain:
                    provider_chain.append(name)

    return JsonResponse(
        {
            "status": "ok",
            "target": target,
            "overrides": response_overrides,
            "provider_chain": provider_chain,
        }
    )
