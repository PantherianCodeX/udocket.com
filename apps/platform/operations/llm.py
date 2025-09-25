from __future__ import annotations

from typing import Dict, Iterable

from django.db import transaction

from .models import LLMProviderSetting


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
