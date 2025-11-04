from __future__ import annotations

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false
from datetime import datetime
from typing import Any

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.platform.operations.llm import (
    delete_llm_configuration,
    delete_org_provider_credential,
    ensure_default_llm_configuration,
    get_llm_configuration,
    get_org_llm_configurations,
    get_org_provider_credentials,
    load_provider_catalog,
    upsert_llm_configuration,
    upsert_org_provider_credential,
)
from packages.udocket_common.json_utils import parse_json_value
from packages.udocket_core.llm import load_llm_settings

from ..auth import ensure_authenticated
from ..contexts import compute_case_tool_state, get_case_and_org
from ..presenters.case_fields import case_field_specs
from .helpers import check_case_update_permission, render_case_panel_with_refresh
from .membership import reconcile_case_memberships


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

    form_errors: dict[str, str] = {}
    case_updates: dict[str, Any] = {}
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
    contributor_ids = set(
        (request.POST.getlist("contributor_ids") or []) if hasattr(request, "POST") else []
    )
    representation_value = (request.POST.get("representation") or "").strip()
    engagement_value = (request.POST.get("engagement_model") or "standard").strip().lower()

    if form_errors:
        state = compute_case_tool_state(request, case, active_tool="intake")
        panel = state["tool_panels"].get("intake")
        if panel:
            panel_body = panel.get("body_context", {})
            panel_body["form_errors"] = form_errors
        return render(request, "platform_ui/tools/_panel.html", {"panel": panel}, status=400)

    update_fields: list[str] = []
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

    state = compute_case_tool_state(request, case, active_tool="intake")
    panel = state["tool_panels"].get("intake")
    if panel is None:
        return render(request, "platform_ui/tools/_panel.html", {"panel": panel})
    return render_case_panel_with_refresh(
        request,
        panel,
        case=case,
        state=state,
        active_tool="intake",
        tools=["intake"],
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

    raw_body = request.body.decode("utf-8") if request.body else "{}"
    parsed_payload = parse_json_value(raw_body or "{}")
    if not isinstance(parsed_payload, dict):
        return HttpResponseBadRequest("Invalid JSON payload.")
    payload = {str(key): value for key, value in parsed_payload.items()}

    target_raw = payload.get("target")
    if not isinstance(target_raw, str) or not target_raw.strip():
        return HttpResponseBadRequest("Missing LLM target.")
    target = target_raw.strip().lower()
    llm_settings = load_llm_settings()
    stage_targets = llm_settings.stage_targets()
    if target not in stage_targets:
        existing_configs = get_org_llm_configurations(str(organization_id), target=target)
        if not existing_configs:
            return HttpResponseBadRequest("Unknown LLM target.")

    action = (payload.get("action") or "upsert").strip().lower()
    config_id = None
    config_payload = payload.get("configuration")
    if isinstance(config_payload, dict):
        config_id = str(config_payload.get("id") or "").strip() or None
    if action == "delete":
        cfg_id = str(payload.get("config_id") or config_id or "").strip()
        if not cfg_id:
            return HttpResponseBadRequest("config_id is required for delete.")
        delete_llm_configuration(organization_id=str(organization_id), config_id=cfg_id)
    else:
        if not isinstance(config_payload, dict):
            return HttpResponseBadRequest("configuration payload is required")
        name = str(config_payload.get("name") or "").strip()
        if not name:
            name = f"{target.title()} configuration"
        description = str(config_payload.get("description") or "").strip()
        stage_map = (
            config_payload.get("stage_map")
            if isinstance(config_payload.get("stage_map"), dict)
            else None
        )
        provider_chain = (
            config_payload.get("provider_chain")
            if isinstance(config_payload.get("provider_chain"), list)
            else None
        )
        set_default = bool(config_payload.get("set_default"))
        updated_config = upsert_llm_configuration(
            organization_id=str(organization_id),
            name=name,
            description=description,
            target=target,
            stage_map=stage_map,
            provider_chain=provider_chain,
            config_id=config_id,
            set_default=set_default,
        )
        if updated_config and updated_config.get("is_default"):
            config_id = updated_config["id"]

    active_config = get_llm_configuration(
        organization_id=str(organization_id),
        config_id=None,
        target=target,
    )
    if not active_config:
        active_config = ensure_default_llm_configuration(
            organization_id=str(organization_id),
            target=target,
            llm_settings=llm_settings,
        )
    configs = get_org_llm_configurations(str(organization_id), target=target)

    return JsonResponse(
        {
            "status": "ok",
            "target": target,
            "configurations": configs,
            "active": active_config,
        }
    )


@require_http_methods(["GET", "POST"])
def case_llm_providers(request: HttpRequest, case_id: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)

    permission_denied = check_case_update_permission(request, case)
    if permission_denied:
        return permission_denied

    catalog = load_provider_catalog()
    credentials = get_org_provider_credentials(case.organization_id)

    if request.method == "GET":
        return JsonResponse(
            {
                "catalog": catalog,
                "credentials": credentials,
            }
        )

    parsed_payload = parse_json_value(request.body.decode("utf-8") if request.body else "{}")
    if not isinstance(parsed_payload, dict):
        return HttpResponseBadRequest("Invalid payload format.")
    payload = {str(key): value for key, value in parsed_payload.items()}

    provider_key = str(payload.get("provider") or "").strip().lower()
    if not provider_key:
        return HttpResponseBadRequest("Provider is required.")

    display_name = str(
        payload.get("display_name")
        or catalog.get(provider_key, {}).get("display_name")
        or provider_key
    )
    endpoint = str(
        payload.get("endpoint") or catalog.get(provider_key, {}).get("default_endpoint") or ""
    ).strip()
    api_key = payload.get("api_key")
    if api_key == "":  # allow clearing key
        api_key = None
    models_payload = payload.get("models")
    if models_payload is None:
        models_payload = catalog.get(provider_key, {}).get("models") or []
    metadata = payload.get("metadata") or {}

    credential = upsert_org_provider_credential(
        organization_id=str(case.organization_id),
        provider=provider_key,
        display_name=display_name,
        endpoint=endpoint,
        api_key=api_key,
        models=models_payload,
        metadata=metadata,
    )

    credentials = get_org_provider_credentials(case.organization_id)

    return JsonResponse(
        {
            "status": "ok",
            "credential": credential,
            "credentials": credentials,
        }
    )


@require_http_methods(["POST"])
def case_llm_provider_delete(request: HttpRequest, case_id: str, provider: str) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    case, _ = get_case_and_org(request, case_id)

    permission_denied = check_case_update_permission(request, case)
    if permission_denied:
        return permission_denied

    delete_org_provider_credential(str(case.organization_id), provider)

    credentials = get_org_provider_credentials(case.organization_id)

    return JsonResponse({"status": "ok", "credentials": credentials})
