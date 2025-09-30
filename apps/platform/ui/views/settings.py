from __future__ import annotations

import json
from typing import Any, Dict, List

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.platform.accounts.utils import resolve_request_organization
from apps.platform.operations.llm import (
    delete_llm_configuration,
    delete_org_provider_credential,
    ensure_default_llm_configuration,
    get_llm_configuration,
    get_org_llm_configurations,
    get_org_provider_credentials,
    load_provider_catalog,
    build_provider_registry,
    upsert_llm_configuration,
    upsert_org_provider_credential,
)
from packages.udocket_core.llm import LLMSettings, load_llm_settings

from .auth import ensure_authenticated


def _stage_slug(stage_key: str) -> str:
    return stage_key.replace(".", "__")


def _stage_field(stage_key: str, suffix: str) -> str:
    return f"stage__{_stage_slug(stage_key)}__{suffix}"


def _parse_json_field(raw_value: str, default: Any, errors: List[str], label: str) -> Any:
    if not raw_value:
        return default
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        errors.append(f"{label}: {exc}")
        return default


def _gather_stage_targets(llm_settings: LLMSettings) -> Dict[str, List[str]]:
    grouped: Dict[str, List[str]] = {}
    for assignment in llm_settings.assignments.values():
        grouped.setdefault(assignment.target, []).append(assignment.stage_key)
    for target, keys in grouped.items():
        grouped[target] = sorted(set(keys))
    return grouped


@require_http_methods(["GET", "POST"])
def organization_settings(request: HttpRequest) -> HttpResponse:
    auth_response = ensure_authenticated(request)
    if auth_response:
        return auth_response

    try:
        organization = resolve_request_organization(request, required=True)
    except PermissionDenied:
        messages.error(request, "Select an organization before opening settings.")
        return redirect("ui-index")

    llm_settings = load_llm_settings()
    stage_targets = _gather_stage_targets(llm_settings)

    provider_catalog = load_provider_catalog()
    provider_credentials = get_org_provider_credentials(str(organization.id))
    provider_registry = build_provider_registry(
        organization_id=str(organization.id),
        llm_settings=llm_settings,
        provider_catalog=provider_catalog,
        provider_credentials=provider_credentials,
    )

    # Handle POST actions --------------------------------------------------
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        errors: List[str] = []
        if action == "provider-upsert":
            provider_key = (request.POST.get("provider") or "").strip().lower()
            if not provider_key:
                errors.append("Provider key is required.")
            display_name = (request.POST.get("display_name") or provider_key).strip() or provider_key
            endpoint = (request.POST.get("endpoint") or "").strip()
            api_key_value = request.POST.get("api_key")
            if request.POST.get("clear_api_key"):
                api_key_value = ""
            models_json = (request.POST.get("models_json") or "").strip()
            metadata_json = (request.POST.get("metadata_json") or "").strip()
            models_payload = _parse_json_field(models_json, [], errors, "Models JSON")
            metadata_payload = _parse_json_field(metadata_json, {}, errors, "Metadata JSON")
            if not errors and provider_key:
                try:
                    upsert_org_provider_credential(
                        organization_id=str(organization.id),
                        provider=provider_key,
                        display_name=display_name,
                        endpoint=endpoint,
                        api_key=api_key_value,
                        models=models_payload,
                        metadata=metadata_payload,
                    )
                    messages.success(request, f"Provider '{provider_key}' saved.")
                except ValueError as exc:  # pragma: no cover - defensive
                    errors.append(str(exc))
        elif action == "provider-delete":
            provider_key = (request.POST.get("provider") or "").strip().lower()
            if provider_key:
                delete_org_provider_credential(str(organization.id), provider_key)
                messages.success(request, f"Provider '{provider_key}' deleted.")
            else:
                errors.append("Provider key is required for deletion.")
        elif action == "config-delete":
            config_id = (request.POST.get("config_id") or "").strip()
            if config_id:
                delete_llm_configuration(
                    organization_id=str(organization.id),
                    config_id=config_id,
                )
                messages.success(request, "Configuration deleted.")
            else:
                errors.append("Missing configuration id.")
        elif action == "config-save":
            target = (request.POST.get("target") or "").strip().lower()
            stage_keys = stage_targets.get(target, [])
            if not stage_keys:
                errors.append("Unknown LLM target.")
            name = (request.POST.get("name") or "").strip() or f"{target.title()} configuration"
            description = (request.POST.get("description") or "").strip()
            config_id = (request.POST.get("config_id") or "").strip() or None
            provider_chain = [value.strip().lower() for value in request.POST.getlist("provider_chain") if value.strip()]
            stage_map: Dict[str, Dict[str, Any]] = {}
            for stage_key in stage_keys:
                provider_value = (request.POST.get(_stage_field(stage_key, "provider")) or "").strip().lower()
                model_value = (request.POST.get(_stage_field(stage_key, "model")) or "").strip()
                max_tokens_raw = (request.POST.get(_stage_field(stage_key, "max_tokens")) or "").strip()
                temperature_raw = (request.POST.get(_stage_field(stage_key, "temperature")) or "").strip()
                options_json = (request.POST.get(_stage_field(stage_key, "options")) or "").strip()
                entry: Dict[str, Any] = {}
                if provider_value:
                    entry["provider"] = provider_value
                if model_value:
                    entry["model"] = model_value
                if max_tokens_raw:
                    try:
                        parsed = int(max_tokens_raw)
                        if parsed > 0:
                            entry["max_tokens"] = parsed
                    except ValueError:
                        errors.append(f"{stage_key}: max tokens must be an integer.")
                if temperature_raw:
                    try:
                        entry.setdefault("options", {})
                        entry["options"]["temperature"] = float(temperature_raw)
                    except ValueError:
                        errors.append(f"{stage_key}: temperature must be numeric.")
                if options_json:
                    options_payload = _parse_json_field(options_json, None, errors, f"{stage_key} options")
                    if isinstance(options_payload, dict):
                        entry.setdefault("options", {}).update(options_payload)
                if entry:
                    stage_map[stage_key] = entry
            set_default = bool(request.POST.get("set_default"))
            if not errors and stage_keys:
                updated = upsert_llm_configuration(
                    organization_id=str(organization.id),
                    name=name,
                    description=description,
                    target=target,
                    stage_map=stage_map,
                    provider_chain=provider_chain,
                    config_id=config_id,
                    set_default=set_default,
                )
                if updated:
                    if updated.get("is_default"):
                        messages.success(request, f"{target.title()} configuration updated and set as default.")
                    else:
                        messages.success(request, f"{target.title()} configuration saved.")
        else:
            errors.append("Unknown action.")

        for error in errors:
            messages.error(request, error)
        return redirect(reverse("ui-organization-settings"))

    # Refresh data for rendering ------------------------------------------
    provider_credentials = get_org_provider_credentials(str(organization.id))
    provider_registry = build_provider_registry(
        organization_id=str(organization.id),
        llm_settings=llm_settings,
        provider_catalog=provider_catalog,
        provider_credentials=provider_credentials,
    )

    provider_options = [
        {
            "value": name,
            "label": entry.get("label", name),
            "available": entry.get("available", False),
            "configured": entry.get("configured", False),
            "endpoint": entry.get("endpoint"),
            "description": entry.get("description"),
        }
        for name, entry in provider_registry.items()
    ]

    stage_targets_context: List[Dict[str, Any]] = []
    for target, stage_keys in sorted(stage_targets.items()):
        active_config = get_llm_configuration(
            organization_id=str(organization.id),
            config_id=None,
            target=target,
        )
        if not active_config:
            active_config = ensure_default_llm_configuration(
                organization_id=str(organization.id),
                target=target,
                llm_settings=llm_settings,
            )
        configurations = get_org_llm_configurations(str(organization.id), target=target)
        stage_map = active_config.get("stage_map", {}) if active_config else {}
        provider_chain = active_config.get("provider_chain", []) if active_config else []

        stage_entries: List[Dict[str, Any]] = []
        for stage_key in stage_keys:
            assignment = llm_settings.stage(stage_key)
            selected = stage_map.get(stage_key, {})
            selected_options = selected.get("options") if isinstance(selected.get("options"), dict) else {}
            field_provider = _stage_field(stage_key, "provider")
            field_model = _stage_field(stage_key, "model")
            field_max_tokens = _stage_field(stage_key, "max_tokens")
            field_temperature = _stage_field(stage_key, "temperature")
            field_options = _stage_field(stage_key, "options")
            stage_entries.append(
                {
                    "key": stage_key,
                    "slug": _stage_slug(stage_key),
                    "label": assignment.label if assignment else stage_key,
                    "description": assignment.description if assignment else "",
                    "selected_provider": selected.get("provider") or (assignment.providers[0] if assignment and assignment.providers else ""),
                    "selected_model": selected.get("model") or (assignment.model if assignment else ""),
                    "selected_max_tokens": selected.get("max_tokens"),
                    "selected_temperature": selected_options.get("temperature"),
                    "selected_options_json": json.dumps(selected_options, indent=2) if selected_options else "",
                    "field_provider": field_provider,
                    "field_model": field_model,
                    "field_max_tokens": field_max_tokens,
                    "field_temperature": field_temperature,
                    "field_options": field_options,
                }
            )

        stage_targets_context.append(
            {
                "target": target,
                "label": target.title(),
                "provider_chain": provider_chain,
                "stage_entries": stage_entries,
                "configurations": configurations,
                "active_config": active_config,
            }
        )

    # Build model options (provider grouped) for selects
    model_options: List[Dict[str, Any]] = []
    for provider_name, entry in provider_registry.items():
        for model in entry.get("models") or []:
            model_options.append(
                {
                    "value": model.get("value"),
                    "label": model.get("label") or model.get("value"),
                    "provider": provider_name,
                    "provider_label": entry.get("label", provider_name),
                }
            )

    context = {
        "organization": organization,
        "provider_catalog": provider_catalog,
        "provider_registry": provider_registry,
        "provider_credentials": provider_credentials,
        "provider_options": provider_options,
        "model_options": model_options,
        "stage_targets": stage_targets_context,
    }
    return render(request, "platform_ui/settings/organization.html", context)
