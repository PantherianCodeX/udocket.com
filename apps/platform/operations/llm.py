from __future__ import annotations

from __future__ import annotations

import json
from typing import Dict, Iterable, List, Optional

from django.db import transaction

from packages.udocket_core.llm.config import PROVIDERS_PATH

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


def get_provider_secret(organization_id: str, provider: str) -> Optional[Dict[str, str]]:
    try:
        record = LLMProviderCredential.objects.get(organization_id=organization_id, provider=provider)
    except LLMProviderCredential.DoesNotExist:
        return None
    return {
        "endpoint": record.endpoint,
        "api_key": decrypt_secret(record.api_key_encrypted),
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
