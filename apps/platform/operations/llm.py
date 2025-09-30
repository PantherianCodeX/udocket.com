from __future__ import annotations

import json
from typing import Dict, Iterable, List, Optional, Sequence

from django.db import transaction

from packages.udocket_core.llm.config import PROVIDERS_PATH, load_llm_settings

try:
    from packages.udocket_core.agents.summarize_lib import DISALLOWED_PROVIDERS as _SUMMARIZE_DISALLOWED_PROVIDERS
except Exception:  # pragma: no cover - fallback when summarizer unavailable
    _SUMMARIZE_DISALLOWED_PROVIDERS = set()

from .crypto import decrypt_secret, encrypt_secret
from .models import LLMProviderCredential, LLMConfiguration


def _clean_stage_map(payload: Dict[str, Dict[str, object]] | None) -> Dict[str, Dict[str, object]]:
    if not isinstance(payload, dict):
        return {}
    cleaned: Dict[str, Dict[str, object]] = {}
    for stage_key, cfg in payload.items():
        if not isinstance(cfg, dict):
            continue
        provider = str(cfg.get("provider") or "").strip().lower()
        model = str(cfg.get("model") or "").strip()
        entry: Dict[str, object] = {}
        options_raw = cfg.get("options") if isinstance(cfg.get("options"), dict) else {}
        options: Dict[str, object] = {}
        for opt_key, opt_value in (options_raw or {}).items():
            key_str = str(opt_key or "").strip()
            if not key_str:
                continue
            if opt_value is None or opt_value == "":
                continue
            options[key_str] = opt_value
        max_tokens_value = cfg.get("max_tokens")
        if isinstance(max_tokens_value, (int, float, str)):
            try:
                parsed_max = int(float(str(max_tokens_value).strip()))
            except (TypeError, ValueError):
                parsed_max = 0
            if parsed_max > 0:
                entry["max_tokens"] = parsed_max
        if provider:
            entry["provider"] = provider
        if model:
            entry["model"] = model
        if options:
            entry["options"] = options
        if entry:
            cleaned[stage_key] = entry
    return cleaned


def _normalize_provider_chain(provider_chain: Iterable[str] | None) -> List[str]:
    chain: List[str] = []
    if not provider_chain:
        return chain
    for value in provider_chain:
        name = str(value or "").strip().lower()
        if not name or name in chain:
            continue
        chain.append(name)
    return chain


def serialize_llm_configuration(config: LLMConfiguration) -> Dict[str, object]:
    return {
        "id": str(config.id),
        "name": config.name,
        "description": config.description,
        "target": config.target,
        "stage_map": dict(config.stage_map or {}),
        "provider_chain": list(config.provider_chain or []),
        "is_default": bool(config.is_default),
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


def get_org_llm_configurations(
    organization_id: str | None,
    *,
    target: str | None = None,
) -> List[Dict[str, object]]:
    if not organization_id:
        return []
    queryset = LLMConfiguration.objects.filter(organization_id=organization_id)
    if target:
        queryset = queryset.filter(target=target)
    queryset = queryset.order_by("-is_default", "name")
    return [serialize_llm_configuration(config) for config in queryset.iterator()]


def get_llm_configuration(
    *,
    organization_id: str | None,
    config_id: str | None,
    target: str | None = None,
) -> Dict[str, object] | None:
    if not organization_id:
        return None
    if not config_id:
        qs = LLMConfiguration.objects.filter(organization_id=organization_id)
        if target:
            qs = qs.filter(target=target)
        config = qs.order_by("-is_default", "name").first()
        return serialize_llm_configuration(config) if config else None
    try:
        config = LLMConfiguration.objects.get(
            organization_id=organization_id, id=config_id
        )
    except LLMConfiguration.DoesNotExist:
        return None
    if target and config.target != target:
        return None
    return serialize_llm_configuration(config)


def upsert_llm_configuration(
    *,
    organization_id: str,
    name: str,
    target: str,
    stage_map: Dict[str, Dict[str, object]] | None,
    provider_chain: Iterable[str] | None,
    description: str | None = None,
    config_id: str | None = None,
    set_default: bool = False,
) -> Dict[str, object]:
    cleaned_map = _clean_stage_map(stage_map)
    chain = _normalize_provider_chain(provider_chain)

    if config_id:
        try:
            config = LLMConfiguration.objects.get(
                organization_id=organization_id, id=config_id
            )
        except LLMConfiguration.DoesNotExist:
            config = None
        if config:
            config.name = name
            config.description = description or ""
            config.target = target
            config.stage_map = cleaned_map
            config.provider_chain = chain
            if set_default:
                LLMConfiguration.objects.filter(
                    organization_id=organization_id,
                    target=target,
                ).update(is_default=False)
                config.is_default = True
            config.save(update_fields=[
                "name",
                "description",
                "target",
                "stage_map",
                "provider_chain",
                "is_default",
                "updated_at",
            ])
            return serialize_llm_configuration(config)

    if set_default:
        LLMConfiguration.objects.filter(
            organization_id=organization_id,
            target=target,
        ).update(is_default=False)

    config = LLMConfiguration.objects.create(
        organization_id=organization_id,
        name=name,
        description=description or "",
        target=target,
        stage_map=cleaned_map,
        provider_chain=chain,
        is_default=set_default,
    )
    return serialize_llm_configuration(config)


def delete_llm_configuration(*, organization_id: str, config_id: str) -> None:
    LLMConfiguration.objects.filter(
        organization_id=organization_id, id=config_id
    ).delete()


def ensure_default_llm_configuration(
    *,
    organization_id: str,
    target: str,
    stage_map: Dict[str, Dict[str, object]] | None = None,
    provider_chain: Iterable[str] | None = None,
    llm_settings=None,
) -> Dict[str, object] | None:
    existing = LLMConfiguration.objects.filter(
        organization_id=organization_id,
        target=target,
        is_default=True,
    ).first()
    if existing:
        return serialize_llm_configuration(existing)

    candidate = LLMConfiguration.objects.filter(
        organization_id=organization_id,
        target=target,
    ).order_by("name").first()
    if candidate:
        candidate.is_default = True
        candidate.save(update_fields=["is_default", "updated_at"])
        return serialize_llm_configuration(candidate)

    if stage_map is None and llm_settings is not None:
        generated: Dict[str, Dict[str, object]] = {}
        for assignment in llm_settings.assignments.values():
            primary = assignment.providers[0] if assignment.providers else ""
            generated[assignment.stage_key] = {
                "provider": primary,
                "model": assignment.model or "",
            }
        stage_map = generated

    cleaned_map = _clean_stage_map(stage_map)
    chain = _normalize_provider_chain(provider_chain)
    if not chain and llm_settings is not None:
        for assignment in llm_settings.assignments.values():
            primary = assignment.providers[0] if assignment.providers else ""
            if primary:
                chain.append(primary)

    if not cleaned_map and not chain:
        return None

    config = LLMConfiguration.objects.create(
        organization_id=organization_id,
        name=f"{target.title()} default",
        description="Automatically generated default LLM configuration",
        target=target,
        stage_map=cleaned_map,
        provider_chain=chain,
        is_default=True,
    )
    return serialize_llm_configuration(config)


def _provider_catalog() -> Dict[str, dict]:
    try:
        data = PROVIDERS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return {}
    return payload.get("providers", {})


def load_provider_catalog() -> Dict[str, dict]:
    return _provider_catalog()


def get_org_provider_credentials(organization_id: str | None) -> Dict[str, Dict[str, object]]:
    if not organization_id:
        return {}
    creds: Dict[str, Dict[str, object]] = {}
    qs = LLMProviderCredential.objects.filter(organization_id=organization_id)
    for record in qs.iterator():
        creds[record.provider] = {
            "provider": record.provider,
            "display_name": record.display_name,
            "endpoint": record.endpoint,
            "models": list(record.models_payload or []),
            "has_api_key": bool(record.api_key_encrypted),
            "metadata": record.metadata or {},
            "is_enabled": record.is_enabled,
        }
    return creds


def _catalog_models_to_options(models) -> List[Dict[str, object]]:
    options: List[Dict[str, object]] = []
    for model_name, model_meta in models.items():
        label = getattr(model_meta, "label", None) or (
            model_meta.get("label") if isinstance(model_meta, dict) else None
        )
        cost_tier = getattr(model_meta, "cost_tier", None) or (
            model_meta.get("cost_tier") if isinstance(model_meta, dict) else None
        )
        max_output = getattr(model_meta, "max_output_tokens", None) or (
            model_meta.get("max_output_tokens") if isinstance(model_meta, dict) else None
        )
        context_window = getattr(model_meta, "context_window_tokens", None) or (
            model_meta.get("context_window_tokens") if isinstance(model_meta, dict) else None
        )
        default_temp = getattr(model_meta, "default_temperature", None) or (
            model_meta.get("default_temperature") if isinstance(model_meta, dict) else None
        )
        origin = getattr(model_meta, "origin", None) or (
            model_meta.get("origin") if isinstance(model_meta, dict) else None
        )
        default_enabled = getattr(model_meta, "default_enabled", None)
        if default_enabled is None and isinstance(model_meta, dict):
            default_enabled = model_meta.get("default_enabled")
        options_payload = getattr(model_meta, "options", None) or (
            model_meta.get("options") if isinstance(model_meta, dict) else None
        )
        options.append(
            {
                "name": model_name,
                "value": model_name,
                "label": label or model_name,
                "cost_tier": cost_tier or "standard",
                "max_output_tokens": max_output,
                "context_window_tokens": context_window,
                "default_temperature": default_temp,
                "origin": origin,
                "enabled": bool(default_enabled) if default_enabled is not None else True,
                "options": options_payload if isinstance(options_payload, dict) else {},
            }
        )
    return options


def _credential_models_to_options(models: Sequence[dict]) -> List[Dict[str, object]]:
    options: List[Dict[str, object]] = []
    for item in models:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("id") or "").strip()
        if not name:
            continue
        options.append(
            {
                "name": name,
                "value": name,
                "label": item.get("label") or name,
                "cost_tier": item.get("cost_tier") or "standard",
                "max_output_tokens": item.get("max_output_tokens"),
                "context_window_tokens": item.get("context_window_tokens"),
                "max_input_tokens": item.get("max_input_tokens"),
                "max_chunk_chars": item.get("max_chunk_chars"),
                "chunk_overlap_tokens": item.get("chunk_overlap_tokens"),
                "max_prompt_chars": item.get("max_prompt_chars"),
                "max_prompt_segments": item.get("max_prompt_segments"),
                "default_temperature": item.get("default_temperature"),
                "origin": item.get("origin"),
                "enabled": item.get("enabled", True),
                "deployment_env": item.get("deployment_env"),
                "options": item.get("options") or {},
            }
        )
    return options


def default_models_payload(provider) -> List[dict]:
    payload: List[dict] = []
    models = getattr(provider, "models", {}) or {}
    for model_name, model_meta in models.items():
        label = getattr(model_meta, "label", None) or (
            model_meta.get("label") if isinstance(model_meta, dict) else None
        )
        cost_tier = getattr(model_meta, "cost_tier", None) or (
            model_meta.get("cost_tier") if isinstance(model_meta, dict) else None
        )
        max_output = getattr(model_meta, "max_output_tokens", None) or (
            model_meta.get("max_output_tokens") if isinstance(model_meta, dict) else None
        )
        context_window = getattr(model_meta, "context_window_tokens", None) or (
            model_meta.get("context_window_tokens") if isinstance(model_meta, dict) else None
        )
        default_temp = getattr(model_meta, "default_temperature", None) or (
            model_meta.get("default_temperature") if isinstance(model_meta, dict) else None
        )
        origin = getattr(model_meta, "origin", None) or (
            model_meta.get("origin") if isinstance(model_meta, dict) else None
        )
        default_enabled = getattr(model_meta, "default_enabled", None)
        if default_enabled is None and isinstance(model_meta, dict):
            default_enabled = model_meta.get("default_enabled")
        options_payload = getattr(model_meta, "options", None) or (
            model_meta.get("options") if isinstance(model_meta, dict) else None
        )
        payload.append(
            {
                "name": model_name,
                "label": label or model_name,
                "cost_tier": cost_tier or "standard",
                "max_output_tokens": max_output,
                "context_window_tokens": context_window,
                "default_temperature": default_temp,
                "origin": origin,
                "enabled": bool(default_enabled) if default_enabled is not None else True,
                "options": options_payload if isinstance(options_payload, dict) else {},
            }
        )
    return payload


def ensure_provider_templates(
    *,
    organization_id: str | None,
    llm_settings=None,
) -> None:
    if not organization_id:
        return
    llm_settings = llm_settings or load_llm_settings()
    for provider_name, provider in llm_settings.providers.items():
        LLMProviderCredential.objects.get_or_create(
            organization_id=organization_id,
            provider=provider_name,
            defaults={
                "display_name": provider.display_name,
                "endpoint": provider.default_endpoint or "",
                "models_payload": default_models_payload(provider),
                "metadata": {},
                "is_enabled": False,
            },
        )


def evaluate_provider_setup(
    *,
    provider,
    endpoint: str | None,
    has_api_key: bool,
    metadata: Optional[dict],
    models: Optional[Iterable[dict]],
) -> Dict[str, object]:
    issues: List[str] = []
    metadata_dict: Dict[str, object] = {}
    if isinstance(metadata, dict):
        metadata_dict = {str(k): v for k, v in metadata.items()}
    endpoint_value = (endpoint or "").strip()
    if not endpoint_value:
        endpoint_value = (provider.default_endpoint or "").strip()
    if provider.api_kind == "azure_openai":
        if not endpoint_value:
            issues.append("Azure endpoint is required")
        elif "<" in endpoint_value or ">" in endpoint_value:
            issues.append("Replace the placeholder resource name in the Azure endpoint")
        deployment = metadata_dict.get("azure_deployment") or metadata_dict.get("default_deployment")
        if not deployment:
            issues.append("Add an Azure deployment name in provider metadata or stage options")
    if provider.requires_api_key and not has_api_key:
        issues.append("API key is required")

    sanitized_models = _normalize_models(models)
    if not sanitized_models:
        sanitized_models = default_models_payload(provider)
    if not sanitized_models:
        issues.append("Add at least one model before enabling this provider")
    else:
        any_enabled = any(
            m.get("enabled", True) for m in sanitized_models if isinstance(m, dict)
        )
        if not any_enabled:
            issues.append("Enable at least one model before enabling this provider")
    return {
        "ready": not issues,
        "issues": issues,
        "endpoint": endpoint_value,
        "metadata": metadata_dict,
        "models": sanitized_models,
    }


def build_provider_registry(
    *,
    organization_id: str | None,
    llm_settings=None,
    provider_catalog: Optional[Dict[str, Dict[str, object]]] = None,
    provider_credentials: Optional[Dict[str, Dict[str, object]]] = None,
    supported_providers: Optional[Sequence[str]] = None,
) -> Dict[str, Dict[str, object]]:
    """Return a merged view of catalog + credential providers for UI/runtime.

    The resulting mapping is keyed by provider name and includes availability
    metadata so callers do not need to duplicate the merge logic.
    """

    llm_settings = llm_settings or load_llm_settings()
    provider_catalog = provider_catalog or load_provider_catalog()
    provider_credentials = provider_credentials or get_org_provider_credentials(organization_id)
    if supported_providers is None:
        supported_set = {
            name
            for name in llm_settings.providers.keys()
            if name not in _SUMMARIZE_DISALLOWED_PROVIDERS
        }
    else:
        supported_set = {
            name
            for name in supported_providers
            if name not in _SUMMARIZE_DISALLOWED_PROVIDERS
        }

    registry: Dict[str, Dict[str, object]] = {}

    for provider_name, provider in llm_settings.providers.items():
        catalog_entry = provider_catalog.get(provider_name, {})
        credential_entry = provider_credentials.get(provider_name, {})
        analysis = evaluate_provider_setup(
            provider=provider,
            endpoint=credential_entry.get("endpoint"),
            has_api_key=bool(credential_entry.get("has_api_key")),
            metadata=credential_entry.get("metadata"),
            models=credential_entry.get("models"),
        )
        is_ready = bool(analysis.get("ready"))
        stored_enabled = bool(credential_entry.get("is_enabled"))
        enabled = stored_enabled and is_ready
        runtime_supported = provider_name in supported_set or bool(credential_entry)
        base_available = provider.is_available() or bool(credential_entry)
        available = runtime_supported and base_available and enabled
        if not is_ready:
            status = "not_configured"
        elif enabled:
            status = "enabled"
        else:
            status = "disabled"
        reason = ""
        if not runtime_supported:
            reason = "Not supported yet"
        elif not base_available:
            reason = "Configure runtime credentials"
        elif status == "not_configured":
            reason = "; ".join(str(msg) for msg in analysis.get("issues") or [])
        elif status == "disabled":
            reason = "Disabled"
        if available:
            reason = ""

        registry[provider_name] = {
            "value": provider_name,
            "label": provider.display_name,
            "available": available,
            "supported": runtime_supported,
            "configured": is_ready,
            "enabled": enabled,
            "status": status,
            "default_endpoint": provider.default_endpoint or catalog_entry.get("default_endpoint"),
            "requires_api_key": bool(
                catalog_entry.get("requires_api_key")
                if "requires_api_key" in catalog_entry
                else provider.requires_api_key
            ),
            "unavailable_reason": reason,
            "endpoint": credential_entry.get("endpoint"),
            "models": _catalog_models_to_options(provider.models),
            "source": "catalog",
            "api_kind": provider.api_kind,
            "description": provider.description or catalog_entry.get("description", ""),
            "can_enable": is_ready,
            "issues": analysis.get("issues") or [],
            "category": getattr(provider, "category", "creator"),
            "hosted_creators": list(getattr(provider, "hosted_creators", [])),
        }

    for provider_name, credential in provider_credentials.items():
        if provider_name in registry:
            existing = registry[provider_name]
            existing_models = existing.get("models") or []
            merged_models: Dict[str, Dict[str, object]] = {}
            for item in existing_models:
                value = str(item.get("value") or "") if isinstance(item, dict) else ""
                if value:
                    merged_models[value] = dict(item)
            for item in _credential_models_to_options(credential.get("models") or []):
                value = str(item.get("value") or "")
                if value:
                    merged_models[value] = item
            if merged_models:
                existing["models"] = list(merged_models.values())
            if credential.get("endpoint"):
                existing["endpoint"] = credential.get("endpoint")
            existing["enabled"] = bool(credential.get("is_enabled")) and existing.get("configured", False)
            if not existing.get("configured"):
                existing["status"] = "not_configured"
            else:
                existing["status"] = "enabled" if existing["enabled"] else "disabled"
            existing["available"] = (
                existing.get("available", False)
                or (existing["enabled"] and existing.get("supported", False))
            )
            if existing["status"] == "disabled":
                existing["unavailable_reason"] = "Disabled"
            continue

        registry[provider_name] = {
            "value": provider_name,
            "label": credential.get("display_name") or provider_name,
            "available": True,
            "supported": True,
            "configured": bool(credential.get("is_enabled")),
            "enabled": bool(credential.get("is_enabled")),
            "status": "enabled" if credential.get("is_enabled") else "disabled",
            "default_endpoint": credential.get("endpoint") or credential.get("default_endpoint"),
            "requires_api_key": True,
            "unavailable_reason": "",
            "endpoint": credential.get("endpoint"),
            "models": _credential_models_to_options(credential.get("models") or []),
            "source": "credential",
            "api_kind": credential.get("api_kind") or "custom",
            "description": credential.get("description") or "",
            "can_enable": bool(credential.get("has_api_key")),
            "issues": [],
            "category": credential.get("category") or "custom",
            "hosted_creators": credential.get("hosted_creators") or [],
        }

    return registry


def get_provider_secret_with_metadata(
    organization_id: str, provider: str
) -> Optional[Dict[str, object]]:
    try:
        record = LLMProviderCredential.objects.get(organization_id=organization_id, provider=provider)
    except LLMProviderCredential.DoesNotExist:
        return None
    return {
        "endpoint": record.endpoint,
        "api_key": decrypt_secret(record.api_key_encrypted),
        "models": list(record.models_payload or []),
        "metadata": dict(record.metadata or {}),
    }


def get_provider_secret(organization_id: str, provider: str) -> Optional[Dict[str, str]]:
    details = get_provider_secret_with_metadata(organization_id, provider)
    if not details:
        return None
    return {
        "endpoint": details.get("endpoint", ""),
        "api_key": details.get("api_key", ""),
    }


def _normalize_models(models: Optional[Iterable[dict]]) -> List[dict]:
    sanitized: List[dict] = []
    if not models:
        return sanitized
    for item in models:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("id") or "").strip()
        if not name:
            continue
        payload: Dict[str, object] = {
            "name": name,
            "label": str(item.get("label") or name),
            "cost_tier": str(item.get("cost_tier") or "standard"),
        }

        def _int_field(source_key: str) -> int | None:
            raw = item.get(source_key)
            if raw in (None, ""):
                return None
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None

        def _float_field(source_key: str) -> float | None:
            raw = item.get(source_key)
            if raw in (None, ""):
                return None
            try:
                return float(raw)
            except (TypeError, ValueError):
                return None

        max_tokens = _int_field("max_output_tokens")
        if max_tokens is not None:
            payload["max_output_tokens"] = max_tokens

        ctx_tokens = _int_field("context_window_tokens")
        if ctx_tokens is not None:
            payload["context_window_tokens"] = ctx_tokens

        input_tokens = _int_field("max_input_tokens")
        if input_tokens is not None:
            payload["max_input_tokens"] = input_tokens

        chunk_chars = _int_field("max_chunk_chars")
        if chunk_chars is not None:
            payload["max_chunk_chars"] = chunk_chars

        chunk_overlap = _int_field("chunk_overlap_tokens")
        if chunk_overlap is not None:
            payload["chunk_overlap_tokens"] = chunk_overlap

        prompt_chars = _int_field("max_prompt_chars")
        if prompt_chars is not None:
            payload["max_prompt_chars"] = prompt_chars

        prompt_segments = _int_field("max_prompt_segments")
        if prompt_segments is not None:
            payload["max_prompt_segments"] = prompt_segments

        default_temp = _float_field("default_temperature")
        if default_temp is not None:
            payload["default_temperature"] = default_temp

        deployment = item.get("deployment_env")
        if deployment:
            payload["deployment_env"] = str(deployment)

        origin = item.get("origin")
        if origin:
            payload["origin"] = str(origin)

        enabled = item.get("enabled")
        if isinstance(enabled, bool):
            payload["enabled"] = enabled
        elif isinstance(enabled, str):
            payload["enabled"] = enabled.lower() not in {"false", "0", "no"}
        else:
            payload["enabled"] = True

        options = item.get("options")
        if isinstance(options, dict):
            payload["options"] = options

        sanitized.append(payload)
    return sanitized


@transaction.atomic
def upsert_org_provider_credential(
    *,
    organization_id: str,
    provider: str,
    display_name: str,
    endpoint: str,
    api_key: Optional[str],
    models: Optional[Iterable[dict]] = None,
    metadata: Optional[dict] = None,
    enabled: Optional[bool] = None,
) -> Dict[str, object]:
    provider = provider.strip().lower()
    if not provider:
        raise ValueError("Provider key is required")

    models_payload = _normalize_models(models)
    encrypted_key = encrypt_secret(api_key)
    enabled_value = bool(enabled) if enabled is not None else True

    record, _created = LLMProviderCredential.objects.get_or_create(
        organization_id=organization_id,
        provider=provider,
        defaults={
            "display_name": display_name,
            "endpoint": endpoint,
            "api_key_encrypted": encrypted_key,
            "models_payload": models_payload,
            "metadata": metadata or {},
            "is_enabled": enabled_value,
        },
    )

    if not _created:
        record.display_name = display_name
        record.endpoint = endpoint
        if api_key is not None:
            record.api_key_encrypted = encrypted_key
        record.models_payload = models_payload
        record.metadata = metadata or {}
        if enabled is not None:
            record.is_enabled = enabled_value
        update_fields = ["display_name", "endpoint", "models_payload", "metadata", "updated_at"]
        if api_key is not None:
            update_fields.append("api_key_encrypted")
        if enabled is not None:
            update_fields.append("is_enabled")
        record.save(update_fields=update_fields)

    return {
        "provider": record.provider,
        "display_name": record.display_name,
        "endpoint": record.endpoint,
        "models": record.models_payload,
        "has_api_key": bool(record.api_key_encrypted),
        "metadata": record.metadata,
        "is_enabled": record.is_enabled,
    }


@transaction.atomic
def delete_org_provider_credential(organization_id: str, provider: str) -> None:
    LLMProviderCredential.objects.filter(
        organization_id=organization_id,
        provider=provider.strip().lower(),
    ).delete()
