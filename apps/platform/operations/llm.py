from __future__ import annotations

import json
from typing import Dict, Iterable, List, Optional, Sequence

from django.db import transaction

from packages.udocket_core.llm.config import PROVIDERS_PATH, load_llm_settings

try:
    from packages.udocket_core.agents.summarize_lib import SUPPORTED_PROVIDERS as _SUMMARIZE_SUPPORTED_PROVIDERS
except Exception:  # pragma: no cover - fallback when summarizer unavailable
    _SUMMARIZE_SUPPORTED_PROVIDERS = {"azure", "local"}

from .crypto import decrypt_secret, encrypt_secret
from .models import LLMProviderSetting, LLMProviderCredential


def get_org_llm_overrides(organization_id: str | None) -> Dict[str, Dict[str, object]]:
    if not organization_id:
        return {}
    overrides: Dict[str, Dict[str, object]] = {}
    qs = LLMProviderSetting.objects.filter(organization_id=organization_id)
    for setting in qs.iterator():
        overrides[setting.stage_key] = {
            "provider": setting.provider,
            "model": setting.model,
            "fallbacks": list(setting.fallbacks or []),
            "allow_offline_fallback": bool(setting.allow_local_fallback),
        }
    return overrides


@transaction.atomic
def set_org_llm_overrides(
    *,
    organization_id: str,
    overrides: Dict[str, Dict[str, object]],
) -> None:
    stage_keys = set(overrides.keys())
    existing: Dict[str, LLMProviderSetting] = {
        obj.stage_key: obj for obj in LLMProviderSetting.objects.filter(organization_id=organization_id)
    }
    to_delete = [obj for key, obj in existing.items() if key not in stage_keys]
    if to_delete:
        LLMProviderSetting.objects.filter(id__in=[obj.id for obj in to_delete]).delete()

    for stage_key, payload in overrides.items():
        provider = str(payload.get("provider") or "").lower()
        model = str(payload.get("model") or "")
        fallbacks = payload.get("fallbacks") or []
        allow_offline = bool(payload.get("allow_offline_fallback"))
        if not provider:
            continue
        if stage_key in existing:
            setting = existing[stage_key]
            setting.provider = provider
            setting.model = model
            setting.fallbacks = list(fallbacks)
            setting.allow_local_fallback = allow_offline
            setting.save(update_fields=["provider", "model", "fallbacks", "allow_local_fallback", "updated_at"])
        else:
            LLMProviderSetting.objects.create(
                organization_id=organization_id,
                stage_key=stage_key,
                provider=provider,
                model=model,
                fallbacks=list(fallbacks),
                allow_local_fallback=allow_offline,
            )


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
        options.append(
            {
                "value": model_name,
                "label": label or model_name,
                "cost_tier": cost_tier or "standard",
                "max_output_tokens": max_output,
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
                "value": name,
                "label": item.get("label") or name,
                "cost_tier": item.get("cost_tier") or "standard",
                "max_output_tokens": item.get("max_output_tokens"),
            }
        )
    return options


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
    supported_set = set(supported_providers or _SUMMARIZE_SUPPORTED_PROVIDERS)

    registry: Dict[str, Dict[str, object]] = {}

    for provider_name, provider in llm_settings.providers.items():
        catalog_entry = provider_catalog.get(provider_name, {})
        credential_entry = provider_credentials.get(provider_name, {})
        configured = provider_name in provider_credentials
        runtime_supported = provider_name in supported_set or provider_name in provider_credentials
        available = runtime_supported and (provider.is_available() or configured)
        reason = ""
        if not runtime_supported:
            reason = "Not supported yet"
        elif not available and not configured:
            reason = "Configure credentials"

        registry[provider_name] = {
            "value": provider_name,
            "label": provider.display_name,
            "available": available,
            "supported": runtime_supported,
            "configured": configured,
            "default_endpoint": catalog_entry.get("default_endpoint"),
            "requires_api_key": bool(catalog_entry.get("requires_api_key", True)),
            "unavailable_reason": reason,
            "endpoint": credential_entry.get("endpoint"),
            "models": _catalog_models_to_options(provider.models),
            "source": "catalog",
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
            existing["configured"] = True
            existing["available"] = existing.get("available", False) or bool(credential)
            continue

        registry[provider_name] = {
            "value": provider_name,
            "label": credential.get("display_name") or provider_name,
            "available": True,
            "supported": True,
            "configured": True,
            "default_endpoint": credential.get("endpoint") or credential.get("default_endpoint"),
            "requires_api_key": True,
            "unavailable_reason": "",
            "endpoint": credential.get("endpoint"),
            "models": _credential_models_to_options(credential.get("models") or []),
            "source": "credential",
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
        sanitized.append(
            {
                "name": name,
                "label": str(item.get("label") or name),
                "cost_tier": str(item.get("cost_tier") or "standard"),
                "max_output_tokens": item.get("max_output_tokens"),
            }
        )
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
) -> Dict[str, object]:
    provider = provider.strip().lower()
    if not provider:
        raise ValueError("Provider key is required")

    models_payload = _normalize_models(models)
    encrypted_key = encrypt_secret(api_key)

    record, _created = LLMProviderCredential.objects.get_or_create(
        organization_id=organization_id,
        provider=provider,
        defaults={
            "display_name": display_name,
            "endpoint": endpoint,
            "api_key_encrypted": encrypted_key,
            "models_payload": models_payload,
            "metadata": metadata or {},
        },
    )

    if not _created:
        record.display_name = display_name
        record.endpoint = endpoint
        if api_key is not None:
            record.api_key_encrypted = encrypted_key
        record.models_payload = models_payload
        record.metadata = metadata or {}
        update_fields = ["display_name", "endpoint", "models_payload", "metadata", "updated_at"]
        if api_key is not None:
            update_fields.append("api_key_encrypted")
        record.save(update_fields=update_fields)

    return {
        "provider": record.provider,
        "display_name": record.display_name,
        "endpoint": record.endpoint,
        "models": record.models_payload,
        "has_api_key": bool(record.api_key_encrypted),
        "metadata": record.metadata,
    }


@transaction.atomic
def delete_org_provider_credential(organization_id: str, provider: str) -> None:
    LLMProviderCredential.objects.filter(
        organization_id=organization_id,
        provider=provider.strip().lower(),
    ).delete()
