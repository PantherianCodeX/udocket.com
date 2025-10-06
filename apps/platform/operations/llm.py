from __future__ import annotations

# pyright: strict

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, TypeAlias, cast

try:  # pragma: no cover - Python < 3.11 fallback
    from typing import NotRequired, Required, TypedDict
except ImportError:  # pragma: no cover - use typing_extensions when stdlib lacks PEP 655 types
    from typing_extensions import NotRequired, Required, TypedDict

from django.db import transaction

from packages.udocket_core.llm.config import (
    LLMProvider,
    LLMProviderModel,
    LLMSettings,
    PROVIDERS_PATH,
    load_llm_settings,
)
from packages.udocket_core.llm.runtime import (
    ChatClientError,
    build_chat_client,
    build_provider_runtime_config,
)
from packages.udocket_core.json_utils import (
    JSONObject,
    JSONValue,
    coerce_float,
    coerce_int,
    coerce_json_object,
    coerce_json_value,
    coerce_object_list,
    coerce_str,
    coerce_str_list,
    normalize_json_object,
    read_json_object,
)

try:
    from packages.udocket_core.agents.analyze_lib import (
        DISALLOWED_PROVIDERS as _analyze_disallowed_providers_source,
    )
except Exception:  # pragma: no cover - fallback when analyzer unavailable
    _analyze_disallowed_providers_source: Iterable[str] = ()
else:
    # already bound by the import alias above
    pass

_ANALYZE_DISALLOWED_PROVIDERS: set[str] = {str(name) for name in _analyze_disallowed_providers_source}

from .crypto import decrypt_secret, encrypt_secret
from .models import LLMConfiguration, LLMProviderCredential


JSONDict: TypeAlias = dict[str, JSONValue]

StageMap: TypeAlias = dict[str, JSONDict]


class ProviderModelOption(TypedDict, total=False):
    name: Required[str]
    value: Required[str]
    label: Required[str]
    cost_tier: Required[str]
    max_output_tokens: NotRequired[int]
    context_window_tokens: NotRequired[int]
    max_input_tokens: NotRequired[int]
    max_chunk_chars: NotRequired[int]
    chunk_overlap_tokens: NotRequired[int]
    max_prompt_chars: NotRequired[int]
    max_prompt_segments: NotRequired[int]
    default_temperature: NotRequired[float]
    origin: NotRequired[str]
    deployment_env: NotRequired[str]
    enabled: NotRequired[bool]
    options: NotRequired[JSONDict]


class SanitizedModel(TypedDict, total=False):
    name: Required[str]
    label: Required[str]
    cost_tier: Required[str]
    max_output_tokens: NotRequired[int]
    context_window_tokens: NotRequired[int]
    max_input_tokens: NotRequired[int]
    max_chunk_chars: NotRequired[int]
    chunk_overlap_tokens: NotRequired[int]
    max_prompt_chars: NotRequired[int]
    max_prompt_segments: NotRequired[int]
    default_temperature: NotRequired[float]
    deployment_env: NotRequired[str]
    origin: NotRequired[str]
    enabled: NotRequired[bool]
    options: NotRequired[JSONDict]


class ProviderCredentialDetails(TypedDict, total=False):
    uid: NotRequired[str]
    provider: str
    display_name: NotRequired[str]
    endpoint: NotRequired[str]
    models: NotRequired[list[JSONDict]]
    has_api_key: NotRequired[bool]
    metadata: NotRequired[JSONDict]
    is_enabled: NotRequired[bool]
    default_endpoint: NotRequired[str]
    api_kind: NotRequired[str]
    description: NotRequired[str]
    category: NotRequired[str]
    hosted_creators: NotRequired[Sequence[str]]


class LLMConfigurationPayload(TypedDict):
    id: str
    name: str
    description: str
    target: str
    stage_map: StageMap
    provider_chain: list[str]
    is_default: bool
    updated_at: str | None


class LiveProbeResult(TypedDict):
    model: str | None
    content: str
    usage: JSONDict


def _serialize_models_payload(models: Iterable[SanitizedModel]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for model in models:
        serialized.append(cast(dict[str, Any], dict(model)))
    return serialized


def _as_mapping_sequence(value: object) -> Sequence[Mapping[str, Any]]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return cast(Sequence[Mapping[str, Any]], value)
    return ()


def _clean_stage_map(payload: Mapping[str, Any] | None) -> StageMap:
    if not payload:
        return {}
    cleaned: StageMap = {}
    for stage_name_raw, cfg in payload.items():
        stage_name = coerce_str(stage_name_raw)
        if not stage_name:
            continue
        if not isinstance(cfg, Mapping):
            continue
        cfg_mapping = cast(Mapping[str, object], cfg)
        cfg_dict = coerce_json_object(cfg_mapping)

        provider_raw = cfg_dict.get("provider")
        provider = coerce_str(provider_raw)
        model_raw = cfg_dict.get("model")
        model = coerce_str(model_raw)

        entry: JSONObject = {}

        options_value = cfg_dict.get("options")
        options = normalize_json_object(
            options_value,
            drop_empty_keys=True,
            drop_nullish_values=True,
        )

        max_tokens_value = cfg_dict.get("max_tokens")
        max_tokens = coerce_int(max_tokens_value)
        if max_tokens is not None and max_tokens > 0:
            entry["max_tokens"] = max_tokens

        if provider:
            entry["provider"] = provider.lower()
        if model:
            entry["model"] = model
        if options:
            entry["options"] = options

        if entry:
            cleaned[stage_name] = entry
    return cleaned


def _model_attr(
    model_meta: LLMProviderModel | Mapping[str, Any],
    attr: str,
) -> object:
    if isinstance(model_meta, LLMProviderModel):
        return getattr(model_meta, attr)
    return model_meta.get(attr)


def _model_options_dict(
    model_meta: LLMProviderModel | Mapping[str, Any]
) -> JSONDict:
    options_value = _model_attr(model_meta, "options")
    if isinstance(options_value, Mapping):
        mapping_value = cast(Mapping[object, object], options_value)
        options_dict: JSONDict = {}
        for key, value in mapping_value.items():
            options_dict[str(key)] = coerce_json_value(value)
        return options_dict
    return {}


def _is_truthy_flag(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() not in {"false", "0", "no"}
    return bool(value)


def _normalize_provider_chain(provider_chain: Iterable[str] | None) -> list[str]:
    chain: list[str] = []
    if not provider_chain:
        return chain
    for value in provider_chain:
        name = str(value or "").strip().lower()
        if not name or name in chain:
            continue
        chain.append(name)
    return chain


def serialize_llm_configuration(config: LLMConfiguration) -> LLMConfigurationPayload:
    raw_stage_map = config.stage_map
    stage_map = _clean_stage_map(cast(Mapping[str, Any] | None, raw_stage_map))
    provider_chain = [
        provider.strip().lower()
        for provider in (config.provider_chain or [])
        if provider.strip()
    ]
    updated_at = config.updated_at.isoformat() if config.updated_at else None
    return {
        "id": str(config.id),
        "name": config.name,
        "description": config.description,
        "target": config.target,
        "stage_map": stage_map,
        "provider_chain": provider_chain,
        "is_default": bool(config.is_default),
        "updated_at": updated_at,
    }


def get_org_llm_configurations(
    organization_id: str | None,
    *,
    target: str | None = None,
) -> list[LLMConfigurationPayload]:
    if not organization_id:
        return []
    queryset = LLMConfiguration.typed_objects().filter(organization_id=organization_id)
    if target:
        queryset = queryset.filter(target=target)
    queryset = queryset.order_by("-is_default", "name")
    return [serialize_llm_configuration(config) for config in queryset.iterator()]


def get_llm_configuration(
    *,
    organization_id: str | None,
    config_id: str | None,
    target: str | None = None,
) -> LLMConfigurationPayload | None:
    if not organization_id:
        return None
    if not config_id:
        qs = LLMConfiguration.typed_objects().filter(organization_id=organization_id)
        if target:
            qs = qs.filter(target=target)
        config = qs.order_by("-is_default", "name").first()
        return serialize_llm_configuration(config) if config else None
    try:
        config = LLMConfiguration.typed_objects().get(
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
    stage_map: Mapping[str, Mapping[str, object]] | None,
    provider_chain: Iterable[str] | None,
    description: str | None = None,
    config_id: str | None = None,
    set_default: bool = False,
) -> LLMConfigurationPayload:
    cleaned_map = _clean_stage_map(stage_map)
    chain = _normalize_provider_chain(provider_chain)

    if config_id:
        try:
            config = LLMConfiguration.typed_objects().get(
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
                LLMConfiguration.typed_objects().filter(
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
        LLMConfiguration.typed_objects().filter(
            organization_id=organization_id,
            target=target,
        ).update(is_default=False)

    config = LLMConfiguration.typed_objects().create(
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
    LLMConfiguration.typed_objects().filter(
        organization_id=organization_id, id=config_id
    ).delete()


def ensure_default_llm_configuration(
    *,
    organization_id: str,
    target: str,
    stage_map: Mapping[str, Mapping[str, object]] | None = None,
    provider_chain: Iterable[str] | None = None,
    llm_settings: LLMSettings | None = None,
) -> LLMConfigurationPayload | None:
    existing = LLMConfiguration.typed_objects().filter(
        organization_id=organization_id,
        target=target,
        is_default=True,
    ).first()
    if existing:
        return serialize_llm_configuration(existing)

    candidate = LLMConfiguration.typed_objects().filter(
        organization_id=organization_id,
        target=target,
    ).order_by("name").first()
    if candidate:
        candidate.is_default = True
        candidate.save(update_fields=["is_default", "updated_at"])
        return serialize_llm_configuration(candidate)

    if stage_map is None and llm_settings is not None:
        generated: StageMap = {}
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

    config = LLMConfiguration.typed_objects().create(
        organization_id=organization_id,
        name=f"{target.title()} default",
        description="Automatically generated default LLM configuration",
        target=target,
        stage_map=cleaned_map,
        provider_chain=chain,
        is_default=True,
    )
    return serialize_llm_configuration(config)


def _provider_catalog() -> dict[str, JSONDict]:
    try:
        payload = read_json_object(PROVIDERS_PATH)
    except OSError:
        return {}
    providers_payload = payload.get("providers")
    if not isinstance(providers_payload, Mapping):
        return {}
    catalog: dict[str, JSONDict] = {}
    for provider_name_obj, provider_cfg in providers_payload.items():
        if isinstance(provider_cfg, Mapping):
            catalog[provider_name_obj] = coerce_json_object(provider_cfg)
        else:
            catalog[provider_name_obj] = {}
    return catalog


def load_provider_catalog() -> dict[str, JSONDict]:
    return _provider_catalog()


def get_org_provider_credentials(
    organization_id: str | None,
) -> dict[str, ProviderCredentialDetails]:
    if not organization_id:
        return {}
    creds: dict[str, ProviderCredentialDetails] = {}
    qs = LLMProviderCredential.typed_objects().filter(organization_id=organization_id)
    for record in qs.iterator():
        raw_models = record.models_payload or []
        models_payload = coerce_object_list(raw_models)
        metadata_payload = coerce_json_object(record.metadata)
        creds[record.provider] = {
            "uid": str(record.uid),
            "provider": record.provider,
            "display_name": record.display_name,
            "endpoint": record.endpoint,
        "models": models_payload,
        "has_api_key": bool(record.api_key_encrypted),
        "metadata": metadata_payload,
        "is_enabled": record.is_enabled,
    }
    return creds


def _catalog_models_to_options(
    models: Mapping[str, LLMProviderModel | Mapping[str, Any]]
) -> list[ProviderModelOption]:
    options: list[ProviderModelOption] = []
    for model_name, model_meta in models.items():
        label_raw = _model_attr(model_meta, "label")
        cost_tier_raw = _model_attr(model_meta, "cost_tier")
        max_output = coerce_int(_model_attr(model_meta, "max_output_tokens"))
        context_window = coerce_int(_model_attr(model_meta, "context_window_tokens"))
        max_input_tokens = coerce_int(_model_attr(model_meta, "max_input_tokens"))
        max_chunk_chars = coerce_int(_model_attr(model_meta, "max_chunk_chars"))
        chunk_overlap_tokens = coerce_int(_model_attr(model_meta, "chunk_overlap_tokens"))
        max_prompt_chars = coerce_int(_model_attr(model_meta, "max_prompt_chars"))
        max_prompt_segments = coerce_int(_model_attr(model_meta, "max_prompt_segments"))
        default_temp = coerce_float(_model_attr(model_meta, "default_temperature"))
        origin_raw = _model_attr(model_meta, "origin")
        deployment_env_raw = _model_attr(model_meta, "deployment_env")
        default_enabled_raw = _model_attr(model_meta, "default_enabled")
        options_dict = _model_options_dict(model_meta)
        deployment_env = str(deployment_env_raw) if isinstance(deployment_env_raw, str) else None
        if deployment_env and "azure_deployment" not in options_dict:
            options_dict["azure_deployment"] = deployment_env

        entry: ProviderModelOption = {
            "name": model_name,
            "value": model_name,
            "label": str(label_raw) if isinstance(label_raw, str) and label_raw else model_name,
            "cost_tier": str(cost_tier_raw) if isinstance(cost_tier_raw, str) and cost_tier_raw else "standard",
            "options": options_dict,
        }

        if max_output is not None:
            entry["max_output_tokens"] = max_output
        if context_window is not None:
            entry["context_window_tokens"] = context_window
        if max_input_tokens is not None:
            entry["max_input_tokens"] = max_input_tokens
        if max_chunk_chars is not None:
            entry["max_chunk_chars"] = max_chunk_chars
        if chunk_overlap_tokens is not None:
            entry["chunk_overlap_tokens"] = chunk_overlap_tokens
        if max_prompt_chars is not None:
            entry["max_prompt_chars"] = max_prompt_chars
        if max_prompt_segments is not None:
            entry["max_prompt_segments"] = max_prompt_segments
        if default_temp is not None:
            entry["default_temperature"] = default_temp
        if isinstance(origin_raw, str) and origin_raw:
            entry["origin"] = origin_raw
        if deployment_env:
            entry["deployment_env"] = deployment_env

        if isinstance(default_enabled_raw, bool):
            entry["enabled"] = default_enabled_raw
        elif isinstance(default_enabled_raw, str):
            entry["enabled"] = default_enabled_raw.lower() not in {"false", "0", "no"}
        else:
            entry["enabled"] = True

        options.append(entry)
    return options


def _credential_models_to_options(
    models: Sequence[Mapping[str, Any]]
) -> list[ProviderModelOption]:
    options: list[ProviderModelOption] = []
    for item in models:
        name_value = item.get("name") or item.get("id")
        name = str(name_value).strip() if isinstance(name_value, str) else ""
        if not name:
            continue
        deployment_env_value = item.get("deployment_env")
        deployment_env = (
            str(deployment_env_value)
            if isinstance(deployment_env_value, str)
            else None
        )
        options_value = item.get("options")
        options_dict = normalize_json_object(options_value, drop_empty_keys=True, drop_nullish_values=True)
        if deployment_env and "azure_deployment" not in options_dict:
            options_dict["azure_deployment"] = deployment_env

        entry: ProviderModelOption = {
            "name": name,
            "value": name,
            "label": str(item.get("label")) if isinstance(item.get("label"), str) else name,
            "cost_tier": str(item.get("cost_tier")) if isinstance(item.get("cost_tier"), str) else "standard",
            "options": options_dict,
        }

        max_output_tokens = coerce_int(item.get("max_output_tokens"))
        if max_output_tokens is not None:
            entry["max_output_tokens"] = max_output_tokens

        context_window_tokens = coerce_int(item.get("context_window_tokens"))
        if context_window_tokens is not None:
            entry["context_window_tokens"] = context_window_tokens

        max_input_tokens = coerce_int(item.get("max_input_tokens"))
        if max_input_tokens is not None:
            entry["max_input_tokens"] = max_input_tokens

        max_chunk_chars = coerce_int(item.get("max_chunk_chars"))
        if max_chunk_chars is not None:
            entry["max_chunk_chars"] = max_chunk_chars

        chunk_overlap_tokens = coerce_int(item.get("chunk_overlap_tokens"))
        if chunk_overlap_tokens is not None:
            entry["chunk_overlap_tokens"] = chunk_overlap_tokens

        max_prompt_chars = coerce_int(item.get("max_prompt_chars"))
        if max_prompt_chars is not None:
            entry["max_prompt_chars"] = max_prompt_chars

        max_prompt_segments = coerce_int(item.get("max_prompt_segments"))
        if max_prompt_segments is not None:
            entry["max_prompt_segments"] = max_prompt_segments

        default_temp = coerce_float(item.get("default_temperature"))
        if default_temp is not None:
            entry["default_temperature"] = default_temp

        origin_value = item.get("origin")
        if isinstance(origin_value, str) and origin_value:
            entry["origin"] = origin_value
        if deployment_env:
            entry["deployment_env"] = deployment_env

        enabled_value = item.get("enabled")
        if isinstance(enabled_value, bool):
            entry["enabled"] = enabled_value
        elif isinstance(enabled_value, str):
            entry["enabled"] = enabled_value.lower() not in {"false", "0", "no"}
        else:
            entry["enabled"] = True

        options.append(entry)
    return options


def default_models_payload(provider: LLMProvider) -> list[SanitizedModel]:
    payload: list[SanitizedModel] = []
    models = provider.models or {}
    for model_name, model_meta in models.items():
        label = model_meta.label or model_name
        cost_tier = model_meta.cost_tier or "standard"
        entry: SanitizedModel = {
            "name": model_name,
            "label": label,
            "cost_tier": cost_tier,
        }

        if model_meta.max_output_tokens is not None:
            entry["max_output_tokens"] = model_meta.max_output_tokens
        if model_meta.context_window_tokens is not None:
            entry["context_window_tokens"] = model_meta.context_window_tokens
        if model_meta.max_input_tokens is not None:
            entry["max_input_tokens"] = model_meta.max_input_tokens
        if model_meta.max_chunk_chars is not None:
            entry["max_chunk_chars"] = model_meta.max_chunk_chars
        if model_meta.chunk_overlap_tokens is not None:
            entry["chunk_overlap_tokens"] = model_meta.chunk_overlap_tokens
        if model_meta.max_prompt_chars is not None:
            entry["max_prompt_chars"] = model_meta.max_prompt_chars
        if model_meta.max_prompt_segments is not None:
            entry["max_prompt_segments"] = model_meta.max_prompt_segments
        if model_meta.default_temperature is not None:
            entry["default_temperature"] = model_meta.default_temperature
        if model_meta.origin:
            entry["origin"] = model_meta.origin
        if model_meta.deployment_env:
            entry["deployment_env"] = model_meta.deployment_env

        options_dict = _model_options_dict(model_meta)
        if model_meta.deployment_env and "azure_deployment" not in options_dict:
            options_dict["azure_deployment"] = model_meta.deployment_env
        if options_dict:
            entry["options"] = options_dict

        entry["enabled"] = bool(model_meta.default_enabled)
        payload.append(entry)
    return payload


def ensure_provider_templates(
    *,
    organization_id: str | None,
    llm_settings: LLMSettings | None = None,
) -> None:
    """Previously ensured provider credentials existed; now a no-op."""
    return


def evaluate_provider_setup(
    *,
    provider: LLMProvider,
    endpoint: str | None,
    has_api_key: bool,
    metadata: Mapping[str, object] | None,
    models: Iterable[Mapping[str, object]] | None,
) -> JSONDict:
    issues: list[str] = []
    metadata_dict = normalize_json_object(metadata, drop_empty_keys=True)
    endpoint_value = (endpoint or "").strip()
    if not endpoint_value:
        endpoint_value = (provider.default_endpoint or "").strip()
    if provider.api_kind == "azure_openai":
        if not endpoint_value:
            issues.append("Azure endpoint is required")
        elif "<" in endpoint_value or ">" in endpoint_value:
            issues.append("Replace the placeholder resource name in the Azure endpoint")
        # Determine whether a deployment is provided either in provider metadata
        # or in at least one enabled model's options/payload.
        deployment = metadata_dict.get("azure_deployment") or metadata_dict.get("default_deployment")
        if not deployment:
            # Look for deployment on any enabled model
            try:
                candidate_models = _normalize_models(models)
            except Exception:
                candidate_models = []
            for model_entry in candidate_models:
                if not _is_truthy_flag(model_entry.get("enabled", True)):
                    continue
                options_entry = model_entry.get("options")
                if isinstance(options_entry, Mapping):
                    azure_option = options_entry.get("azure_deployment")
                    if isinstance(azure_option, str) and azure_option.strip():
                        deployment = azure_option.strip()
                        break
                deployment_env = model_entry.get("deployment_env")
                if isinstance(deployment_env, str) and deployment_env.strip():
                    deployment = deployment_env.strip()
                    break
        if not deployment:
            issues.append("Add an Azure deployment name in provider metadata or model options")
    if provider.requires_api_key and not has_api_key:
        issues.append("API key is required")

    sanitized_models = _normalize_models(models)
    if not sanitized_models:
        sanitized_models = default_models_payload(provider)
    if not sanitized_models:
        issues.append("Add at least one model before enabling this provider")
    else:
        any_enabled = any(
            _is_truthy_flag(model.get("enabled", True)) for model in sanitized_models
        )
        if not any_enabled:
            issues.append("Enable at least one model before enabling this provider")
    issues_json: list[JSONValue] = [s for s in issues]
    models_json: list[JSONValue] = [coerce_json_object(m) for m in sanitized_models]
    return {
        "ready": not issues,
        "issues": issues_json,
        "endpoint": endpoint_value,
        "metadata": metadata_dict,
        "models": models_json,
    }


def build_provider_registry(
    *,
    organization_id: str | None,
    llm_settings: LLMSettings | None = None,
    provider_catalog: Mapping[str, JSONDict] | None = None,
    provider_credentials: Mapping[str, ProviderCredentialDetails] | None = None,
    supported_providers: Sequence[str] | None = None,
) -> dict[str, JSONDict]:
    """Return a merged view of catalog + credential providers for UI/runtime.

    The resulting mapping is keyed by provider name and includes availability
    metadata so callers do not need to duplicate the merge logic.
    """

    settings = llm_settings or load_llm_settings()
    catalog = provider_catalog or load_provider_catalog()
    credentials_map = provider_credentials or get_org_provider_credentials(organization_id)
    if supported_providers is None:
        supported_set = {
            name
            for name in settings.providers.keys()
            if name not in _ANALYZE_DISALLOWED_PROVIDERS
        }
    else:
        supported_set = {
            name
            for name in supported_providers
            if name not in _ANALYZE_DISALLOWED_PROVIDERS
        }

    registry: dict[str, JSONDict] = {}

    for provider_name, provider in settings.providers.items():
        catalog_entry = catalog.get(provider_name, {})
        credential_entry = credentials_map.get(provider_name, {})
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
            issues_list = analysis.get("issues")
            if isinstance(issues_list, Sequence) and not isinstance(issues_list, (str, bytes)):
                reason = "; ".join(str(msg) for msg in issues_list)
        elif status == "disabled":
            reason = "Disabled"
        if available:
            reason = ""

        issues_payload = analysis.get("issues")
        if isinstance(issues_payload, Sequence) and not isinstance(issues_payload, (str, bytes)):
            analysis_issues = [str(msg) for msg in issues_payload]
        else:
            analysis_issues = []

        entry_catalog: dict[str, object] = {
            "value": provider_name,
            "label": provider.display_name,
            "available": available,
            "supported": runtime_supported,
            "configured": is_ready,
            "enabled": enabled,
            "status": status,
            "default_endpoint": provider.default_endpoint
            or catalog_entry.get("default_endpoint"),
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
            "issues": analysis_issues,
            "category": getattr(provider, "category", "creator"),
            "hosted_creators": list(getattr(provider, "hosted_creators", [])),
        }
        registry[provider_name] = {
            k: coerce_json_value(v) for k, v in entry_catalog.items()
        }

    for provider_name, credential in credentials_map.items():
        if provider_name in registry:
            existing = registry[provider_name]
            existing_models_seq = _as_mapping_sequence(existing.get("models"))
            merged_models: dict[str, JSONDict] = {}
            for item in existing_models_seq:
                value = str(item.get("value") or "")
                if value:
                    merged_models[value] = coerce_json_object(item)
            credential_models_seq = _as_mapping_sequence(credential.get("models"))
            for option in _credential_models_to_options(credential_models_seq):
                option_value = option["value"]
                if option_value:
                    merged_models[option_value] = coerce_json_object(option)
            if merged_models:
                existing["models"] = [
                    coerce_json_object(opt) for opt in merged_models.values()
                ]
            endpoint_override = credential.get("endpoint")
            if isinstance(endpoint_override, str) and endpoint_override:
                existing["endpoint"] = endpoint_override
            configured = bool(existing.get("configured"))
            existing["enabled"] = bool(credential.get("is_enabled")) and configured
            if not configured:
                existing["status"] = "not_configured"
            else:
                existing["status"] = "enabled" if existing["enabled"] else "disabled"
            supported = bool(existing.get("supported"))
            existing["available"] = bool(existing.get("available")) or (
                existing["enabled"] and supported
            )
            if existing["status"] == "disabled":
                existing["unavailable_reason"] = "Disabled"
            continue

        credential_models_seq = _as_mapping_sequence(credential.get("models"))
        credential_models_options = _credential_models_to_options(credential_models_seq)
        display_name = coerce_str(credential.get("display_name")) or provider_name
        endpoint_override = coerce_str(credential.get("endpoint"))
        default_endpoint = endpoint_override or coerce_str(credential.get("default_endpoint"))
        api_kind = coerce_str(credential.get("api_kind")) or "custom"
        description = coerce_str(credential.get("description")) or ""
        category = coerce_str(credential.get("category")) or "custom"
        hosted_creators = coerce_str_list(credential.get("hosted_creators") or [])
        has_api_key = bool(credential.get("has_api_key"))
        enabled_flag = bool(credential.get("is_enabled"))

        entry: dict[str, object] = {
            "value": provider_name,
            "label": display_name,
            "available": True,
            "supported": True,
            "configured": enabled_flag,
            "enabled": enabled_flag,
            "status": "enabled" if enabled_flag else "disabled",
            "requires_api_key": True,
            "unavailable_reason": "",
            "models": credential_models_options,
            "source": "credential",
            "api_kind": api_kind,
            "description": description,
            "can_enable": has_api_key,
            "issues": [],
            "category": category,
            "hosted_creators": hosted_creators,
        }
        if default_endpoint:
            entry["default_endpoint"] = default_endpoint
        if endpoint_override:
            entry["endpoint"] = endpoint_override
        registry[provider_name] = {k: coerce_json_value(v) for k, v in entry.items()}

    return registry


def get_provider_secret_with_metadata(
    organization_id: str, provider: str
) -> JSONDict | None:
    try:
        record = LLMProviderCredential.typed_objects().get(
            organization_id=organization_id, provider=provider
        )
    except LLMProviderCredential.DoesNotExist:
        return None
    models_payload = coerce_object_list(record.models_payload or [])
    metadata_payload = coerce_json_object(record.metadata)
    return {
        "endpoint": record.endpoint,
        "api_key": decrypt_secret(record.api_key_encrypted),
        "models": [coerce_json_object(m) for m in models_payload],
        "metadata": metadata_payload,
    }


def get_provider_secret(organization_id: str, provider: str) -> dict[str, str] | None:
    details = get_provider_secret_with_metadata(organization_id, provider)
    if not details:
        return None
    endpoint_value = details.get("endpoint")
    api_key_value = details.get("api_key")
    endpoint_str = endpoint_value if isinstance(endpoint_value, str) else ""
    api_key_str = api_key_value if isinstance(api_key_value, str) else ""
    return {
        "endpoint": endpoint_str,
        "api_key": api_key_str,
    }


def _normalize_models(
    models: Iterable[Mapping[str, Any]] | None,
) -> list[SanitizedModel]:
    sanitized: list[SanitizedModel] = []
    if not models:
        return sanitized
    for item in models:
        name_source = item.get("name") or item.get("id")
        name = str(name_source).strip() if isinstance(name_source, str) else ""
        if not name:
            continue
        label_value = item.get("label")
        label = str(label_value) if isinstance(label_value, str) and label_value else name
        cost_tier_value = item.get("cost_tier")
        cost_tier = (
            str(cost_tier_value)
            if isinstance(cost_tier_value, str) and cost_tier_value
            else "standard"
        )
        payload: SanitizedModel = {
            "name": name,
            "label": label,
            "cost_tier": cost_tier,
        }

        max_output_tokens = coerce_int(item.get("max_output_tokens"))
        if max_output_tokens is not None:
            payload["max_output_tokens"] = max_output_tokens

        context_window_tokens = coerce_int(item.get("context_window_tokens"))
        if context_window_tokens is not None:
            payload["context_window_tokens"] = context_window_tokens

        max_input_tokens = coerce_int(item.get("max_input_tokens"))
        if max_input_tokens is not None:
            payload["max_input_tokens"] = max_input_tokens

        max_chunk_chars = coerce_int(item.get("max_chunk_chars"))
        if max_chunk_chars is not None:
            payload["max_chunk_chars"] = max_chunk_chars

        chunk_overlap_tokens = coerce_int(item.get("chunk_overlap_tokens"))
        if chunk_overlap_tokens is not None:
            payload["chunk_overlap_tokens"] = chunk_overlap_tokens

        max_prompt_chars = coerce_int(item.get("max_prompt_chars"))
        if max_prompt_chars is not None:
            payload["max_prompt_chars"] = max_prompt_chars

        max_prompt_segments = coerce_int(item.get("max_prompt_segments"))
        if max_prompt_segments is not None:
            payload["max_prompt_segments"] = max_prompt_segments

        default_temperature = coerce_float(item.get("default_temperature"))
        if default_temperature is not None:
            payload["default_temperature"] = default_temperature

        deployment_env_value = item.get("deployment_env")
        if isinstance(deployment_env_value, str) and deployment_env_value:
            payload["deployment_env"] = deployment_env_value

        origin_value = item.get("origin")
        if isinstance(origin_value, str) and origin_value:
            payload["origin"] = origin_value

        enabled_value = item.get("enabled")
        if isinstance(enabled_value, bool):
            payload["enabled"] = enabled_value
        elif isinstance(enabled_value, str):
            payload["enabled"] = enabled_value.lower() not in {"false", "0", "no"}
        else:
            payload["enabled"] = True

        options_value = item.get("options")
        options_dict = normalize_json_object(
            options_value, drop_empty_keys=True, drop_nullish_values=True
        )
        if options_dict:
            payload["options"] = options_dict

        sanitized.append(payload)
    return sanitized


def _prepare_live_model_entry(model: SanitizedModel) -> JSONDict:
    mapping_model = cast(Mapping[str, JSONValue], model)
    entry: JSONDict = {key: value for key, value in mapping_model.items()}
    options_value = entry.get("options")
    options = normalize_json_object(options_value, drop_empty_keys=True, drop_nullish_values=True)
    deployment_env = entry.get("deployment_env")
    if isinstance(deployment_env, str) and deployment_env:
        if "azure_deployment" not in options:
            options["azure_deployment"] = deployment_env
    entry["options"] = options
    return entry


def run_live_model_probe(
    *,
    provider: LLMProvider,
    endpoint: str,
    api_key: str,
    metadata: Mapping[str, object] | None,
    model_payload: SanitizedModel,
) -> LiveProbeResult:
    if not api_key:
        raise ChatClientError("Configure an API key before running a live test")
    if not endpoint:
        endpoint = provider.default_endpoint or ""
    metadata_dict = normalize_json_object(metadata, drop_empty_keys=True)
    prepared = _prepare_live_model_entry(model_payload)
    model_name_value = prepared.get("name")
    model_name = str(model_name_value) if isinstance(model_name_value, str) else ""
    options_value = prepared.get("options")
    options_payload = normalize_json_object(options_value, drop_empty_keys=True, drop_nullish_values=True)
    credential_payload: dict[str, Any] = {
        "endpoint": endpoint,
        "api_key": api_key,
        "metadata": metadata_dict,
    }
    runtime_cfg = build_provider_runtime_config(
        provider=provider,
        model_name=model_name,
        credential_payload=credential_payload,
        options=options_payload,
    )
    client = build_chat_client(provider_runtime=runtime_cfg)
    # Choose a safe temperature: prefer explicit option, then model default, else 1.0
    test_temperature = 1.0
    try:
        opt_temp = options_payload.get("temperature")
        if isinstance(opt_temp, (int, float)):
            test_temperature = float(opt_temp)
        else:
            default_temp = prepared.get("default_temperature")
            if isinstance(default_temp, (int, float)):
                test_temperature = float(default_temp)
    except Exception:
        test_temperature = 1.0
    # Pick a reasonable token budget for the probe
    max_out = 0
    try:
        mo = prepared.get("max_output_tokens")
        if isinstance(mo, (int, float)):
            max_out = int(mo)
    except Exception:
        max_out = 0
    safe_max_tokens = max(16, min(256, max_out or 128))

    try:
        content, usage = client.chat(
            messages=[{"role": "user", "content": "Say OK"}],
            temperature=test_temperature,
            max_tokens=safe_max_tokens,
        )
    except ChatClientError:
        raise
    except Exception as exc:  # pragma: no cover - network failures
        raise ChatClientError(f"Live request failed: {exc}") from exc
    usage_payload = normalize_json_object(usage, drop_empty_keys=True)
    model_value = coerce_str(prepared.get("name"))
    result: LiveProbeResult = {
        "model": model_value,
        "content": content.strip(),
        "usage": usage_payload,
    }
    return result


def run_provider_live_test(
    *,
    provider: LLMProvider,
    endpoint: str,
    api_key: str,
    metadata: Mapping[str, object] | None,
    models: Iterable[Mapping[str, object]] | None,
    preferred_model: str | None = None,
) -> LiveProbeResult:
    sanitized = _normalize_models(models)
    if not sanitized:
        sanitized = _normalize_models(default_models_payload(provider))
    target = None
    if preferred_model:
        for item in sanitized:
            if item.get("name") == preferred_model:
                target = item
                break
    if not target:
        for item in sanitized:
            if item.get("enabled", True):
                target = item
                break
    if not target and sanitized:
        target = sanitized[0]
    if not target:
        raise ChatClientError("Add an enabled model before testing this provider")
    return run_live_model_probe(
        provider=provider,
        endpoint=endpoint,
        api_key=api_key,
        metadata=metadata,
        model_payload=target,
    )


@transaction.atomic
def upsert_org_provider_credential(
    *,
    organization_id: str,
    provider: str,
    display_name: str,
    endpoint: str,
    api_key: str | None,
    models: Iterable[Mapping[str, object]] | None = None,
    metadata: Mapping[str, object] | None = None,
    enabled: bool | None = None,
) -> ProviderCredentialDetails:
    provider = provider.strip().lower()
    if not provider:
        raise ValueError("Provider key is required")

    models_payload = _normalize_models(models)
    models_serialized = _serialize_models_payload(models_payload)
    encrypted_key = encrypt_secret(api_key)
    enabled_value = bool(enabled) if enabled is not None else True
    metadata_payload = normalize_json_object(metadata, drop_empty_keys=True)

    record, _created = LLMProviderCredential.typed_objects().get_or_create(
        organization_id=organization_id,
        provider=provider,
        defaults={
            "display_name": display_name,
            "endpoint": endpoint,
            "api_key_encrypted": encrypted_key,
            "models_payload": models_serialized,
            "metadata": metadata_payload,
            "is_enabled": enabled_value,
        },
    )

    if not _created:
        record.display_name = display_name
        record.endpoint = endpoint
        if api_key is not None:
            record.api_key_encrypted = encrypted_key
        record.models_payload = models_serialized
        record.metadata = metadata_payload
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
        "models": coerce_object_list(record.models_payload or []),
        "has_api_key": bool(record.api_key_encrypted),
        "metadata": coerce_json_object(record.metadata),
        "is_enabled": record.is_enabled,
    }


@transaction.atomic
def delete_org_provider_credential(organization_id: str, provider: str) -> None:
    LLMProviderCredential.typed_objects().filter(
        organization_id=organization_id,
        provider=provider.strip().lower(),
    ).delete()


@transaction.atomic
def delete_org_provider_credential_by_uuid(organization_id: str, provider_uid: str) -> None:
    LLMProviderCredential.typed_objects().filter(
        organization_id=organization_id,
        uid=provider_uid,
    ).delete()


@transaction.atomic
def upsert_org_provider_credential_by_uuid(
    *,
    organization_id: str,
    provider_uid: str,
    provider: str,
    display_name: str,
    endpoint: str,
    api_key: str | None,
    models: Iterable[Mapping[str, object]] | None = None,
    metadata: Mapping[str, object] | None = None,
    enabled: bool | None = None,
) -> ProviderCredentialDetails:
    models_payload = _normalize_models(models)
    models_serialized = _serialize_models_payload(models_payload)
    encrypted_key = encrypt_secret(api_key)
    enabled_value = bool(enabled) if enabled is not None else True
    metadata_payload = normalize_json_object(metadata, drop_empty_keys=True)
    try:
        record = LLMProviderCredential.typed_objects().get(
            organization_id=organization_id,
            uid=provider_uid,
        )
    except LLMProviderCredential.DoesNotExist:
        return upsert_org_provider_credential(
            organization_id=organization_id,
            provider=provider,
            display_name=display_name,
            endpoint=endpoint,
            api_key=api_key,
            models=models_payload,
            metadata=metadata_payload,
            enabled=enabled,
        )
    record.provider = provider.strip().lower() or record.provider
    record.display_name = display_name
    record.endpoint = endpoint
    if api_key is not None:
        record.api_key_encrypted = encrypted_key
    record.models_payload = models_serialized
    record.metadata = metadata_payload
    if enabled is not None:
        record.is_enabled = enabled_value
    update_fields = [
        "provider",
        "display_name",
        "endpoint",
        "models_payload",
        "metadata",
        "updated_at",
    ]
    if api_key is not None:
        update_fields.append("api_key_encrypted")
    if enabled is not None:
        update_fields.append("is_enabled")
    record.save(update_fields=update_fields)
    return {
        "provider": record.provider,
        "display_name": record.display_name,
        "endpoint": record.endpoint,
        "models": coerce_object_list(record.models_payload or []),
        "has_api_key": bool(record.api_key_encrypted),
        "metadata": coerce_json_object(record.metadata),
        "is_enabled": record.is_enabled,
    }
