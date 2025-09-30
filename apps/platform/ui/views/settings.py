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
    build_provider_registry,
    default_models_payload,
    delete_llm_configuration,
    delete_org_provider_credential,
    delete_org_provider_credential_by_uuid,
    ensure_default_llm_configuration,
    ensure_provider_templates,
    evaluate_provider_setup,
    get_provider_secret_with_metadata,
    get_llm_configuration,
    get_org_llm_configurations,
    get_org_provider_credentials,
    load_provider_catalog,
    run_live_model_probe,
    run_provider_live_test,
    upsert_llm_configuration,
    upsert_org_provider_credential,
    upsert_org_provider_credential_by_uuid,
)
from packages.udocket_core.llm import LLMSettings, load_llm_settings
from packages.udocket_core.llm.runtime import ChatClientError

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
    return llm_settings.stage_targets()


def _normalize_section(section: str | None, stage_targets: Dict[str, List[str]]) -> str:
    valid: set[str] = {"providers", *stage_targets.keys()}
    if not section:
        return "providers"
    normalized = section.strip().lower()
    return normalized if normalized in valid else "providers"


def _provider_models_from_post(request: HttpRequest) -> List[dict]:
    names = request.POST.getlist("model_name")
    labels = request.POST.getlist("model_label")
    tiers = request.POST.getlist("model_cost_tier")
    max_tokens = request.POST.getlist("model_max_output_tokens")
    ctx_tokens = request.POST.getlist("model_context_window_tokens")
    origins = request.POST.getlist("model_origin")
    default_temps = request.POST.getlist("model_default_temperature")
    max_input_tokens = request.POST.getlist("model_max_input_tokens")
    max_chunk_chars = request.POST.getlist("model_max_chunk_chars")
    chunk_overlap_tokens = request.POST.getlist("model_chunk_overlap_tokens")
    max_prompt_chars = request.POST.getlist("model_max_prompt_chars")
    max_prompt_segments = request.POST.getlist("model_max_prompt_segments")
    deployment_envs = request.POST.getlist("model_deployment_env")
    options_json = request.POST.getlist("model_options_json")
    models: List[dict] = []
    for index, raw_name in enumerate(names):
        name = (raw_name or "").strip()
        if not name:
            continue
        label = labels[index] if index < len(labels) else ""
        tier = tiers[index] if index < len(tiers) else ""
        max_token_raw = max_tokens[index] if index < len(max_tokens) else ""
        ctx_token_raw = ctx_tokens[index] if index < len(ctx_tokens) else ""
        payload: Dict[str, Any] = {
            "name": name,
            "label": (label or name).strip(),
            "cost_tier": (tier or "standard").strip() or "standard",
            "enabled": True,
        }
        if max_token_raw:
            try:
                payload["max_output_tokens"] = int(max_token_raw)
            except ValueError:
                pass
        if ctx_token_raw:
            try:
                payload["context_window_tokens"] = int(ctx_token_raw)
            except ValueError:
                pass
        origin_raw = origins[index] if index < len(origins) else ""
        if origin_raw:
            payload["origin"] = origin_raw.strip()
        temp_raw = default_temps[index] if index < len(default_temps) else ""
        if temp_raw:
            try:
                payload["default_temperature"] = float(temp_raw)
            except ValueError:
                pass

        options_payload: Dict[str, Any] = {}

        def _int_field(source: List[str], container_key: str) -> None:
            raw = source[index] if index < len(source) else ""
            if not raw:
                return
            try:
                value = int(raw)
            except ValueError:
                return
            payload[container_key] = value
            options_payload[container_key] = value

        _int_field(max_input_tokens, "max_input_tokens")
        _int_field(max_chunk_chars, "max_chunk_chars")
        _int_field(chunk_overlap_tokens, "chunk_overlap_tokens")
        _int_field(max_prompt_chars, "max_prompt_chars")
        _int_field(max_prompt_segments, "max_prompt_segments")

        deployment_raw = deployment_envs[index] if index < len(deployment_envs) else ""
        if deployment_raw:
            payload["deployment_env"] = deployment_raw.strip()
            options_payload["azure_deployment"] = deployment_raw.strip()

        options_raw = options_json[index] if index < len(options_json) else ""
        if options_raw:
            try:
                parsed_options = json.loads(options_raw)
                if isinstance(parsed_options, dict):
                    options_payload.update(parsed_options)
            except json.JSONDecodeError:
                pass

        if options_payload:
            payload["options"] = options_payload
        models.append(payload)
    return models


def _extract_provider_form_data(
    request: HttpRequest,
    *,
    existing: Dict[str, Any] | None,
) -> tuple[Dict[str, Any], List[str]]:
    errors: List[str] = []
    provider_key = (request.POST.get("provider") or "").strip().lower()
    provider_uuid = (request.POST.get("provider_uuid") or "").strip()
    display_name = (
        (request.POST.get("display_name") or provider_key).strip() or provider_key
    )
    endpoint = (request.POST.get("endpoint") or "").strip()
    api_key_raw = (request.POST.get("api_key") or "").strip()
    clear_flag = request.POST.get("clear_api_key") in {"1", "true", "on"}
    if clear_flag:
        api_action = "clear"
    elif api_key_raw:
        api_action = "update"
    else:
        api_action = "preserve"

    models_payload_override = (request.POST.get("models_payload") or "").strip()
    models_payload_compiled = (request.POST.get("models_payload_compiled") or "").strip()
    metadata_json = (request.POST.get("metadata_json") or "").strip()
    enabled_flag = request.POST.get("is_enabled")
    if enabled_flag is None:
        enabled_value = bool(existing.get("is_enabled")) if existing else False
    else:
        enabled_value = enabled_flag in {"1", "true", "on"}

    if models_payload_override:
        models_payload = _parse_json_field(
            models_payload_override,
            [],
            errors,
            "Models configuration",
        )
    elif models_payload_compiled:
        models_payload = _parse_json_field(
            models_payload_compiled,
            [],
            errors,
            "Models configuration",
        )
    else:
        models_payload = _provider_models_from_post(request)

    metadata_payload = _parse_json_field(
        metadata_json,
        {},
        errors,
        "Metadata JSON",
    )

    data = {
        "provider_uuid": provider_uuid,
        "provider": provider_key,
        "display_name": display_name,
        "endpoint": endpoint,
        "models": models_payload,
        "metadata": metadata_payload,
        "enabled": enabled_value,
        "api_action": api_action,
        "api_key": api_key_raw,
        "clear_flag": clear_flag,
        "existing_has_api_key": bool(existing.get("has_api_key")) if existing else False,
    }
    return data, errors


@require_http_methods(["GET", "POST"])
def organization_settings(
    request: HttpRequest, section: str | None = None
) -> HttpResponse:
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
    post_section = None
    if request.method == "POST":
        post_section = (
            request.POST.get("section")
            or request.POST.get("target")
        )
    active_section = _normalize_section(
        section or post_section or request.GET.get("section"),
        stage_targets,
    )

    ensure_provider_templates(
        organization_id=str(organization.id),
        llm_settings=llm_settings,
    )

    # Determine selected provider for form defaults
    selected_provider_key = (request.GET.get("provider") or "").strip().lower()
    provider_catalog = load_provider_catalog()
    provider_credentials = get_org_provider_credentials(str(organization.id))
    provider_registry = build_provider_registry(
        organization_id=str(organization.id),
        llm_settings=llm_settings,
        provider_catalog=provider_catalog,
        provider_credentials=provider_credentials,
    )

    nav_items = [
        {
            "key": "providers",
            "label": "LLM providers",
            "url": reverse("ui-organization-settings-section", args=["providers"]),
        }
    ]
    for target_key in sorted(stage_targets.keys()):
        nav_items.append(
            {
                "key": target_key,
                "label": f"{target_key.title()} config",
                "url": reverse("ui-organization-settings-section", args=[target_key]),
            }
        )

    template_options = [
        {
            "value": key,
            "label": (entry.get("display_name") or key.replace("_", " ").title()),
        }
        for key, entry in sorted(provider_catalog.items())
    ]

    nav_primary = nav_items[0] if nav_items else None
    tool_items = [item for item in nav_items if item["key"] != "providers"]
    nav_groups: List[Dict[str, object]] = []
    if tool_items:
        nav_groups.append({
            "label": "Tool configurations",
            "items": tool_items,
        })

    base_context = {
        "organization": organization,
        "nav_items": nav_items,
        "nav_primary": nav_primary,
        "nav_groups": nav_groups,
        "nav_pills": [],
        "active_section": active_section,
        "selected_provider": selected_provider_key,
        "provider_template_options": template_options,
    }

    if request.method == "POST" and active_section == "providers":
        action = (request.POST.get("action") or "").strip()
        provider_key = (request.POST.get("provider") or "").strip().lower()
        selected_provider_key = provider_key or selected_provider_key
        existing_cred = provider_credentials.get(provider_key)
        form_data, parse_errors = _extract_provider_form_data(
            request,
            existing=existing_cred,
        )
        errors: List[str] = list(parse_errors)

        if action == "provider-upsert":
            if not provider_key:
                errors.append("Provider key is required.")
            if not errors and provider_key:
                try:
                    if form_data["api_action"] == "clear":
                        api_key_value: str | None = ""
                    elif form_data["api_action"] == "update":
                        api_key_value = form_data["api_key"]
                    else:
                        api_key_value = None
                    if form_data.get("provider_uuid"):
                        upsert_org_provider_credential_by_uuid(
                            organization_id=str(organization.id),
                            provider_uid=form_data["provider_uuid"],
                            provider=provider_key,
                            display_name=form_data["display_name"],
                            endpoint=form_data["endpoint"],
                            api_key=api_key_value,
                            models=form_data["models"],
                            metadata=form_data["metadata"],
                            enabled=form_data["enabled"],
                        )
                    else:
                        upsert_org_provider_credential(
                            organization_id=str(organization.id),
                            provider=provider_key,
                            display_name=form_data["display_name"],
                            endpoint=form_data["endpoint"],
                            api_key=api_key_value,
                            models=form_data["models"],
                            metadata=form_data["metadata"],
                            enabled=form_data["enabled"],
                        )
                    messages.success(request, f"Provider '{provider_key}' saved.")
                except ValueError as exc:
                    errors.append(str(exc))
        elif action == "provider-delete":
            provider_uuid = form_data.get("provider_uuid")
            if provider_uuid:
                delete_org_provider_credential_by_uuid(str(organization.id), provider_uuid)
            elif provider_key:
                delete_org_provider_credential(str(organization.id), provider_key)
            messages.success(request, f"Provider '{provider_key}' deleted.")
            else:
                errors.append("Provider key is required for deletion.")
        elif action == "provider-toggle":
            desired = request.POST.get("enabled") in {"1", "true", "on"}
            if not provider_key:
                errors.append("Provider key is required for status change.")
            else:
                entry = provider_registry.get(provider_key)
                cred = provider_credentials.get(provider_key)
                if not cred:
                    errors.append("Provider credential not found.")
                else:
                    provider_obj = llm_settings.provider(provider_key)
                    if not provider_obj:
                        errors.append("Unknown provider selected.")
                    else:
                        analysis = evaluate_provider_setup(
                            provider=provider_obj,
                            endpoint=cred.get("endpoint"),
                            has_api_key=bool(cred.get("has_api_key")),
                            metadata=cred.get("metadata"),
                            models=cred.get("models"),
                        )
                        if desired and not analysis.get("ready"):
                            issues = analysis.get("issues") or [
                                "Provider validation failed."
                            ]
                            errors.extend(str(issue) for issue in issues)
                        elif desired and not (entry and entry.get("can_enable")):
                            errors.append(
                                "Complete required settings before enabling this provider."
                            )
                        else:
                            upsert_org_provider_credential(
                                organization_id=str(organization.id),
                                provider=provider_key,
                                display_name=cred.get("display_name") or provider_key,
                                endpoint=cred.get("endpoint") or "",
                                api_key=None,
                                models=cred.get("models") or [],
                                metadata=cred.get("metadata") or {},
                                enabled=desired,
                            )
                            messages.success(
                                request,
                                f"Provider '{provider_key}' {'enabled' if desired else 'disabled'}.",
                            )
        elif action == "provider-test":
            provider_obj = llm_settings.provider(provider_key)
            if not provider_key:
                errors.append("Provider key is required for testing.")
            elif not provider_obj:
                errors.append("Unknown provider selected.")
            elif not errors:
                cred = existing_cred or {}
                secret_details = get_provider_secret_with_metadata(
                    str(organization.id), provider_key
                )
                stored_api_key = (
                    secret_details.get("api_key") if secret_details else ""
                )
                stored_metadata = (
                    secret_details.get("metadata") if secret_details else {}
                )
                effective_endpoint = (
                    form_data["endpoint"]
                    or cred.get("endpoint")
                    or provider_obj.default_endpoint
                    or ""
                )
                metadata_override = (
                    form_data["metadata"]
                    if isinstance(form_data["metadata"], dict) and form_data["metadata"]
                    else None
                )
                if metadata_override is not None:
                    effective_metadata = metadata_override
                else:
                    existing_meta = cred.get("metadata")
                    if isinstance(existing_meta, dict) and existing_meta:
                        effective_metadata = existing_meta
                    else:
                        effective_metadata = (
                            stored_metadata if isinstance(stored_metadata, dict) else {}
                        )
                supplied_models = form_data.get("models") or []
                effective_models = (
                    supplied_models if supplied_models else cred.get("models") or []
                )
                if not effective_models:
                    effective_models = default_models_payload(provider_obj)
                if form_data["api_action"] == "clear":
                    effective_api_key = ""
                elif form_data["api_action"] == "update":
                    effective_api_key = form_data["api_key"].strip()
                else:
                    effective_api_key = stored_api_key
                analysis = evaluate_provider_setup(
                    provider=provider_obj,
                    endpoint=effective_endpoint,
                    has_api_key=bool(effective_api_key),
                    metadata=effective_metadata,
                    models=effective_models,
                )
                if analysis.get("ready"):
                    try:
                        probe = run_provider_live_test(
                            provider=provider_obj,
                            endpoint=effective_endpoint,
                            api_key=effective_api_key,
                            metadata=effective_metadata,
                            models=effective_models,
                        )
                    except ChatClientError as exc:
                        errors.append(str(exc))
                    else:
                        snippet = probe.get("content") or "OK"
                        snippet = snippet if len(snippet) <= 60 else f"{snippet[:57]}..."
                        messages.success(
                            request,
                            f"Provider '{provider_key}' live test succeeded with model "
                            f"{probe.get('model')}: {snippet}",
                        )
                else:
                    issues = analysis.get("issues") or [
                        "Provider validation failed."
                    ]
                    errors.extend(str(issue) for issue in issues)
        elif action == "provider-model-test":
            provider_obj = llm_settings.provider(provider_key)
            if not provider_key:
                errors.append("Provider key is required for testing.")
            elif not provider_obj:
                errors.append("Unknown provider selected.")
            else:
                payload_raw = (request.POST.get("model_test_payload") or "").strip()
                try:
                    model_payload = json.loads(payload_raw) if payload_raw else {}
                except json.JSONDecodeError:
                    errors.append("Invalid model payload provided for testing.")
                    model_payload = {}
                if not model_payload.get("name"):
                    errors.append("Model payload is missing an identifier.")
                if not errors:
                    cred = existing_cred or {}
                    secret_details = get_provider_secret_with_metadata(
                        str(organization.id), provider_key
                    )
                    stored_api_key = (
                        secret_details.get("api_key") if secret_details else ""
                    )
                    stored_metadata = (
                        secret_details.get("metadata") if secret_details else {}
                    )
                    effective_endpoint = (
                        form_data["endpoint"]
                        or cred.get("endpoint")
                        or provider_obj.default_endpoint
                        or ""
                    )
                    metadata_override = (
                        form_data["metadata"]
                        if isinstance(form_data["metadata"], dict) and form_data["metadata"]
                        else None
                    )
                    if metadata_override is not None:
                        effective_metadata = metadata_override
                    else:
                        existing_meta = cred.get("metadata")
                        if isinstance(existing_meta, dict) and existing_meta:
                            effective_metadata = existing_meta
                        else:
                            effective_metadata = (
                                stored_metadata if isinstance(stored_metadata, dict) else {}
                            )
                    supplied_models = form_data.get("models") or []
                    effective_models = (
                        supplied_models if supplied_models else cred.get("models") or []
                    )
                    if not effective_models:
                        effective_models = default_models_payload(provider_obj)
                    if form_data["api_action"] == "clear":
                        effective_api_key = ""
                    elif form_data["api_action"] == "update":
                        effective_api_key = form_data["api_key"].strip()
                    else:
                        effective_api_key = stored_api_key
                    analysis = evaluate_provider_setup(
                        provider=provider_obj,
                        endpoint=effective_endpoint,
                        has_api_key=bool(effective_api_key),
                        metadata=effective_metadata,
                        models=effective_models,
                    )
                    if analysis.get("ready"):
                        try:
                            probe = run_live_model_probe(
                                provider=provider_obj,
                                endpoint=effective_endpoint,
                                api_key=effective_api_key,
                                metadata=effective_metadata,
                                model_payload=model_payload,
                            )
                        except ChatClientError as exc:
                            errors.append(str(exc))
                        else:
                            snippet = probe.get("content") or "OK"
                            snippet = (
                                snippet if len(snippet) <= 60 else f"{snippet[:57]}..."
                            )
                            messages.success(
                                request,
                                f"Model '{probe.get('model')}' live test succeeded: {snippet}",
                            )
                    else:
                        issues = analysis.get("issues") or [
                            "Provider validation failed."
                        ]
                        errors.extend(str(issue) for issue in issues)
        else:
            errors.append("Unknown action.")

        for error in errors:
            messages.error(request, error)
        redirect_url = reverse("ui-organization-settings-section", args=[active_section])
        if selected_provider_key:
            redirect_url = f"{redirect_url}?provider={selected_provider_key}"
        return redirect(redirect_url)

    if request.method == "POST" and active_section != "providers":
        action = (request.POST.get("action") or "").strip()
        errors: List[str] = []
        target = active_section
        stage_keys = stage_targets.get(target, [])
        if action == "config-delete":
            config_id = (request.POST.get("config_id") or "").strip()
            if config_id:
                delete_llm_configuration(
                    organization_id=str(organization.id), config_id=config_id
                )
                messages.success(request, "Configuration deleted.")
            else:
                errors.append("Missing configuration id.")
        elif action in {"config-save", "config-create"}:
            if not stage_keys:
                errors.append("Unknown LLM target.")
            name = (request.POST.get("name") or "").strip() or f"{target.title()} configuration"
            description = (request.POST.get("description") or "").strip()
            config_id = (request.POST.get("config_id") or "").strip() or None
            provider_chain = [
                value.strip().lower()
                for value in request.POST.getlist("provider_chain")
                if value.strip()
            ]
            stage_map: Dict[str, Dict[str, Any]] = {}
            for stage_key in stage_keys:
                provider_value = (
                    (request.POST.get(_stage_field(stage_key, "provider")) or "")
                    .strip()
                    .lower()
                )
                model_value = (
                    request.POST.get(_stage_field(stage_key, "model")) or ""
                ).strip()
                entry: Dict[str, Any] = {}
                if provider_value:
                    entry["provider"] = provider_value
                if model_value:
                    entry["model"] = model_value

                def _int_field(suffix: str) -> int | None:
                    raw = (request.POST.get(_stage_field(stage_key, suffix)) or "").strip()
                    if not raw:
                        return None
                    try:
                        value = int(raw)
                    except ValueError:
                        errors.append(
                            f"{stage_key}: {suffix.replace('_', ' ')} must be an integer."
                        )
                        return None
                    return value if value >= 0 else None

                max_tokens = _int_field("max_tokens")
                if max_tokens is not None and max_tokens > 0:
                    entry["max_tokens"] = max_tokens

                temperature_raw = (
                    request.POST.get(_stage_field(stage_key, "temperature")) or ""
                ).strip()
                if temperature_raw:
                    try:
                        entry.setdefault("options", {})["temperature"] = float(
                            temperature_raw
                        )
                    except ValueError:
                        errors.append(f"{stage_key}: temperature must be numeric.")

                option_mappings = {
                    "opt_max_input_tokens": "max_input_tokens",
                    "opt_max_chunk_chars": "max_chunk_chars",
                    "opt_chunk_overlap_tokens": "chunk_overlap_tokens",
                    "opt_max_prompt_chars": "max_prompt_chars",
                    "opt_max_prompt_segments": "max_prompt_segments",
                    "opt_azure_deployment": "azure_deployment",
                }
                for field_suffix, option_key in option_mappings.items():
                    raw_value = (
                        request.POST.get(_stage_field(stage_key, field_suffix)) or ""
                    ).strip()
                    if not raw_value:
                        continue
                    try:
                        if option_key.startswith("max_") or option_key.endswith("_tokens"):
                            value: Any = int(raw_value)
                        else:
                            value = raw_value
                        entry.setdefault("options", {})[option_key] = value
                    except ValueError:
                        errors.append(
                            f"{stage_key}: {option_key.replace('_', ' ')} must be an integer."
                        )

                options_json = (
                    request.POST.get(_stage_field(stage_key, "options")) or ""
                ).strip()
                if options_json:
                    options_payload = _parse_json_field(
                        options_json, None, errors, f"{stage_key} options"
                    )
                    if isinstance(options_payload, dict):
                        entry.setdefault("options", {}).update(options_payload)

                if entry:
                    stage_map[stage_key] = entry

            set_default = bool(request.POST.get("set_default"))
            if not errors:
                updated = upsert_llm_configuration(
                    organization_id=str(organization.id),
                    name=name,
                    description=description,
                    target=target,
                    stage_map=stage_map,
                    provider_chain=provider_chain,
                    config_id=config_id if action == "config-save" else None,
                    set_default=set_default,
                )
                if updated:
                    if updated.get("is_default"):
                        messages.success(
                            request,
                            f"{target.title()} configuration saved as default.",
                        )
                    else:
                        messages.success(request, f"{target.title()} configuration saved.")
                    return redirect(
                        f"{reverse('ui-organization-settings-section', args=[target])}?config={updated['id']}"
                    )
        else:
            errors.append("Unknown action.")

        for error in errors:
            messages.error(request, error)
        return redirect(reverse("ui-organization-settings-section", args=[target]))

    provider_credentials = get_org_provider_credentials(str(organization.id))
    provider_registry = build_provider_registry(
        organization_id=str(organization.id),
        llm_settings=llm_settings,
        provider_catalog=provider_catalog,
        provider_credentials=provider_credentials,
    )

    origin_overrides = {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "meta": "Meta",
        "mistral": "Mistral",
        "aws": "AWS",
        "ollama": "Ollama",
        "cohere": "Cohere",
        "google": "Google",
        "open_source": "Open Source",
        "amazon": "Amazon",
    }
    creator_labels: Dict[str, str] = {}
    for catalog_entry in provider_catalog.values():
        for model_meta in (catalog_entry.get("models") or {}).values():
            origin = model_meta.get("origin")
            if not origin:
                continue
            label = (
                model_meta.get("origin_label")
                or origin_overrides.get(origin)
                or origin.replace("_", " ").title()
            )
            creator_labels.setdefault(origin, label)
    creator_options = [
        {"value": key, "label": creator_labels[key]} for key in sorted(creator_labels.keys())
    ]
    if "custom" not in creator_labels:
        creator_options.append({"value": "custom", "label": "Custom / Other"})

    if active_section == "providers":
        provider_list: List[Dict[str, Any]] = []
        configured_names = sorted(provider_credentials.keys())
        for name in configured_names:
            cred_entry = provider_credentials.get(name, {})
            registry_entry = provider_registry.get(name, {})
            models_payload = registry_entry.get("models") or []
            normalized_models: List[Dict[str, Any]] = []
            for model_meta in models_payload:
                if not isinstance(model_meta, dict):
                    continue
                options_meta = model_meta.get("options") if isinstance(model_meta.get("options"), dict) else {}
                combined = {
                    **model_meta,
                    "display_max_input_tokens": model_meta.get("max_input_tokens")
                    or options_meta.get("max_input_tokens"),
                    "display_max_chunk_chars": model_meta.get("max_chunk_chars")
                    or options_meta.get("max_chunk_chars"),
                    "display_chunk_overlap_tokens": model_meta.get("chunk_overlap_tokens")
                    or options_meta.get("chunk_overlap_tokens"),
                    "display_max_prompt_chars": model_meta.get("max_prompt_chars")
                    or options_meta.get("max_prompt_chars"),
                    "display_max_prompt_segments": model_meta.get("max_prompt_segments")
                    or options_meta.get("max_prompt_segments"),
                    "display_deployment_env": model_meta.get("deployment_env")
                    or options_meta.get("azure_deployment"),
                }
                normalized_models.append(combined)

            hosted_labels = []
            for creator in registry_entry.get("hosted_creators") or []:
                label = origin_overrides.get(creator) or creator_labels.get(creator)
                if not label:
                    label = creator.replace("_", " ").title()
                hosted_labels.append(label)

            configured_flag = bool(registry_entry.get("configured"))
            enabled_flag = bool(registry_entry.get("enabled")) and configured_flag
            status_value = registry_entry.get("status")
            if not status_value:
                if not configured_flag:
                    status_value = "not_configured"
                elif enabled_flag:
                    status_value = "enabled"
                else:
                    status_value = "disabled"

            provider_list.append(
                {
                    "key": name,
                    "label": cred_entry.get("display_name")
                    or registry_entry.get("label")
                    or name,
                    "status": status_value,
                    "endpoint": cred_entry.get("endpoint")
                    or registry_entry.get("endpoint"),
                    "configured": configured_flag,
                    "enabled": enabled_flag,
                    "available": registry_entry.get("available", False),
                    "models": normalized_models,
                    "models_enabled_count": sum(
                        1 for model in normalized_models if model.get("enabled", True)
                    ),
                    "models_total_count": len(normalized_models),
                    "category": registry_entry.get("category") or "creator",
                    "hosted_creators": hosted_labels,
                    "issues": registry_entry.get("issues") or [],
                    "can_enable": registry_entry.get("can_enable", False),
                    "unavailable_reason": registry_entry.get("unavailable_reason"),
                }
            )

        context = {
            **base_context,
            "provider_catalog": provider_catalog,
            "provider_registry": provider_registry,
            "provider_credentials": provider_credentials,
            "providers": provider_list,
            "selected_provider": selected_provider_key,
            "model_creator_options": creator_options,
        }
        return render(
            request,
            "platform_ui/settings/organization/providers.html",
            context,
        )

    target_key = active_section
    stage_keys = stage_targets.get(target_key, [])
    configurations = get_org_llm_configurations(str(organization.id), target=target_key)
    selected_config_id = request.GET.get("config") or None
    active_config = None
    if selected_config_id:
        active_config = get_llm_configuration(
            organization_id=str(organization.id),
            config_id=selected_config_id,
            target=target_key,
        )
    if not active_config:
        active_config = get_llm_configuration(
            organization_id=str(organization.id),
            config_id=None,
            target=target_key,
        )
        if not active_config:
            active_config = ensure_default_llm_configuration(
                organization_id=str(organization.id),
                target=target_key,
                llm_settings=llm_settings,
            )

    stage_map = active_config.get("stage_map", {}) if active_config else {}
    provider_chain = active_config.get("provider_chain", []) if active_config else []

    enabled_providers = [
        {
            "value": name,
            "label": entry.get("label", name),
        }
        for name, entry in provider_registry.items()
        if entry.get("enabled")
    ]

    stage_entries: List[Dict[str, Any]] = []
    for stage_key in stage_keys:
        assignment = llm_settings.stage(stage_key)
        selected = stage_map.get(stage_key, {})
        selected_options = (
            selected.get("options")
            if isinstance(selected.get("options"), dict)
            else {}
        )
        stage_entries.append(
            {
                "key": stage_key,
                "slug": _stage_slug(stage_key),
                "label": assignment.label if assignment else stage_key,
                "description": assignment.description if assignment else "",
                "selected_provider": selected.get("provider")
                or (
                    assignment.providers[0]
                    if assignment and assignment.providers
                    else ""
                ),
                "selected_model": selected.get("model")
                or (assignment.model if assignment else ""),
                "selected_max_tokens": selected.get("max_tokens"),
                "selected_temperature": selected_options.get("temperature"),
                "selected_options": selected_options,
                "selected_options_json": json.dumps(selected_options, indent=2)
                if selected_options
                else "",
                "field_provider": _stage_field(stage_key, "provider"),
                "field_model": _stage_field(stage_key, "model"),
                "field_max_tokens": _stage_field(stage_key, "max_tokens"),
                "field_temperature": _stage_field(stage_key, "temperature"),
                "field_options": _stage_field(stage_key, "options"),
                "field_opt_max_input_tokens": _stage_field(stage_key, "opt_max_input_tokens"),
                "field_opt_max_chunk_chars": _stage_field(stage_key, "opt_max_chunk_chars"),
                "field_opt_chunk_overlap_tokens": _stage_field(stage_key, "opt_chunk_overlap_tokens"),
                "field_opt_max_prompt_chars": _stage_field(stage_key, "opt_max_prompt_chars"),
                "field_opt_max_prompt_segments": _stage_field(stage_key, "opt_max_prompt_segments"),
                "field_opt_azure_deployment": _stage_field(stage_key, "opt_azure_deployment"),
            }
        )

    model_options: List[Dict[str, Any]] = []
    for provider_name, entry in provider_registry.items():
        if not entry.get("enabled"):
            continue
        for model in entry.get("models") or []:
            if model.get("enabled") is False:
                continue
            model_options.append(
                {
                    "value": model.get("value"),
                    "label": model.get("label") or model.get("value"),
                    "provider": provider_name,
                    "provider_label": entry.get("label", provider_name),
                    "context_window_tokens": model.get("context_window_tokens"),
                    "max_output_tokens": model.get("max_output_tokens"),
                    "origin": model.get("origin"),
                }
            )

    context = {
        **base_context,
        "target": target_key,
        "target_label": target_key.title(),
        "configurations": configurations,
        "active_config": active_config,
        "provider_chain": provider_chain,
        "stage_entries": stage_entries,
        "provider_options": enabled_providers,
        "model_options": model_options,
        "providers_configured": bool(provider_registry),
        "provider_warning": not enabled_providers,
    }
    return render(
        request,
        "platform_ui/settings/organization/target.html",
        context,
    )
