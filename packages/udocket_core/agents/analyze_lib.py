from __future__ import annotations

# pyright: strict
import logging
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Optional, TypedDict, cast

from ..config.paths import resolve_analyze_defaults_path
from .common import parse_transcript, TranscriptParse
from .common.io import TranscriptSegment
from .langgraph_orchestrator import build_analyze_graph, enable_langgraph_debug_logging
from .analyze.utils import FinalizedOutputs, AnalyzePipeline
from packages.udocket_common.json_utils import coerce_json_object, coerce_object_dict, read_json_object
from ..llm import LLMSettings, load_llm_settings
from ..llm.runtime import (
    ChatClient,
    ChatClientError,
    build_chat_client,
    build_provider_runtime_config,
)
from .common.llm_health import ensure_llm_client_health

StageOptions = dict[str, object]
StageMap = dict[str, StageOptions]
ProviderCredentials = Mapping[str, Mapping[str, object]]


def _empty_mapping_proxy() -> MappingProxyType[str, object]:
    return MappingProxyType({})


class StageModelInfo(TypedDict):
    provider: str
    model: str
    context_window_tokens: int | None
    max_output_tokens: int | None
    deployment_env: str | None


class StageCatalogEntry(TypedDict):
    label: str
    description: str
    min_context_tokens: int
    recommended_context_tokens: int
    target_chunk_tokens: int
    output_reserve_tokens: int
    resource_notes: str
    recommended_models: list[StageModelInfo]
    eligible_models: list[StageModelInfo]


def _coerce_string_list(values: object) -> list[str]:
    if isinstance(values, Sequence) and not isinstance(values, (str, bytes, bytearray)):
        result: list[str] = []
        sequence = cast(Sequence[object], values)
        for entry in sequence:
            text = str(entry or "").strip()
            if text:
                result.append(text)
        return result
    return []


def _coerce_int(value: object, fallback: int) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        try:
            parsed = int(float(str(value)))
        except (TypeError, ValueError, AttributeError):
            return fallback
    return parsed if parsed > 0 else fallback


def _coerce_float(value: object, fallback: float) -> float:
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        return fallback
    return parsed


def _normalize_providers(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in values:
        name = (raw or "").strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized

@lru_cache(maxsize=1)
def load_analyze_defaults() -> dict[str, object]:
    payload = read_json_object(resolve_analyze_defaults_path())
    return coerce_object_dict(payload)


def analyze_defaults() -> dict[str, object]:
    return dict(load_analyze_defaults())


_DEFAULTS: dict[str, object] = load_analyze_defaults()


def _int_default(key: str, fallback: int) -> int:
    return _coerce_int(_DEFAULTS.get(key), fallback)


def _float_default(key: str, fallback: float) -> float:
    return _coerce_float(_DEFAULTS.get(key), fallback)


MAX_PROMPT_SEGMENTS = _int_default("max_prompt_segments", 250)
MAX_PROMPT_CHARS = _int_default("max_prompt_chars", 32000)
DEFAULT_TOKENS_TO_CHAR_RATIO = _float_default("chars_per_token", 4.0)
DEFAULT_TEMPERATURE = _float_default("temperature", 1.0)
DEFAULT_MAX_OUTPUT_TOKENS = _int_default("max_output_tokens", 24000)

_DEFAULT_CHAIN = _coerce_string_list(_DEFAULTS.get("default_provider_chain"))
DEFAULT_PROVIDER_CHAIN: list[str] = _normalize_providers(_DEFAULT_CHAIN) or ["azure"]

_STAGE_LIMITS_DEFAULT = coerce_object_dict(_DEFAULTS.get("stage_token_limits"))


def _stage_limit(key: str, fallback: int) -> int:
    return _coerce_int(_STAGE_LIMITS_DEFAULT.get(key), fallback)


DEFAULT_STAGE_TOKEN_LIMITS: dict[str, int] = {
    "analyze.extract_outline": _stage_limit("analyze.extract_outline", 12000),
    "analyze.build_timeline_seeds": _stage_limit("analyze.build_timeline_seeds", 8000),
    "analyze.build_entity_hints": _stage_limit("analyze.build_entity_hints", 8000),
    "analyze.draft_markdown": _stage_limit("analyze.draft_markdown", 12000),
    "analyze.qa_and_finalize": _stage_limit("analyze.qa_and_finalize", 6000),
}
LLM_STAGE_KEYS = {
    "context_builder": "analyze.context_builder",
    "extract_outline": "analyze.extract_outline",
    "build_timeline_seeds": "analyze.build_timeline_seeds",
    "build_entity_hints": "analyze.build_entity_hints",
    "draft_markdown": "analyze.draft_markdown",
    "qa_and_finalize": "analyze.qa_and_finalize",
}
_llm_settings_cache: Optional[LLMSettings] = None

_STAGE_ALIAS_LOOKUP: dict[str, str] = {}
for _attr, _stage_key in LLM_STAGE_KEYS.items():
    _STAGE_ALIAS_LOOKUP[_attr.lower()] = _stage_key
    _STAGE_ALIAS_LOOKUP[_stage_key.lower()] = _stage_key
    if _stage_key.startswith("analyze."):
        _STAGE_ALIAS_LOOKUP[_stage_key.split(".", 1)[1].lower()] = _stage_key


@dataclass(frozen=True)
class StageOverride:
    providers: tuple[str, ...] = ()
    model: str | None = None
    options: Mapping[str, object] = field(default_factory=_empty_mapping_proxy)
    max_tokens: int | None = None

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, object] | None,
    ) -> StageOverride | None:
        if not payload:
            return None

        providers_candidate: list[str] = []
        raw_providers = payload.get("providers")
        if isinstance(raw_providers, Sequence) and not isinstance(
            raw_providers, (str, bytes, bytearray)
        ):
            for entry in cast(Sequence[object], raw_providers):
                provider_name = str(entry or "").strip()
                if provider_name:
                    providers_candidate.append(provider_name)

        raw_provider = payload.get("provider")
        if isinstance(raw_provider, str):
            single_provider = raw_provider.strip()
            if single_provider:
                providers_candidate.append(single_provider)

        normalized_providers = tuple(_normalize_providers(providers_candidate))

        model_value: object | None = payload.get("model")
        model = str(model_value).strip() if isinstance(model_value, str) else None
        if model == "":
            model = None

        options_payload = payload.get("options")
        if isinstance(options_payload, Mapping):
            option_items = cast(Mapping[object, object], options_payload)
            options = MappingProxyType(
                {
                    str(key): value
                    for key, value in option_items.items()
                    if key is not None
                }
            )
        else:
            options = _empty_mapping_proxy()

        max_tokens_value = payload.get("max_tokens") or payload.get("max_output_tokens")
        max_tokens = None
        if max_tokens_value is not None:
            parsed = _coerce_int(max_tokens_value, 0)
            if parsed > 0:
                max_tokens = parsed

        if (
            not normalized_providers
            and model is None
            and not options
            and max_tokens is None
        ):
            return None

        return cls(
            providers=normalized_providers,
            model=model,
            options=options,
            max_tokens=max_tokens,
        )


def _build_stage_override_index(stage_map: StageMap) -> dict[str, StageOverride]:
    overrides: dict[str, StageOverride] = {}
    for key, options in stage_map.items():
        canonical = _normalize_stage_identifier(key) or key
        override = StageOverride.from_mapping(options)
        if override is None:
            continue
        overrides.setdefault(canonical, override)
    return overrides


DISALLOWED_PROVIDERS: set[str] = set()


def _normalize_stage_map(
    stage_map: Mapping[str, Mapping[str, object]] | None,
) -> StageMap:
    if not stage_map:
        return {}

    normalized: StageMap = {}
    prefix_defaults: list[tuple[str | None, StageOptions]] = []

    for raw_key, value in stage_map.items():
        value_dict = coerce_object_dict(value)
        if not value_dict:
            continue
        key = str(raw_key or "").strip()
        if not key:
            continue
        lowered = key.lower()
        if lowered in {"*", "default"}:
            prefix_defaults.append((None, dict(value_dict)))
            continue
        if lowered.endswith(".*"):
            prefix = lowered[:-2].strip()
            if prefix:
                prefix_defaults.append((prefix, dict(value_dict)))
            continue

        canonical = _normalize_stage_identifier(key)
        normalized_key = canonical or key
        cfg = dict(value_dict)
        normalized[normalized_key] = cfg
        if canonical:
            attr = canonical.split(".", 1)[1] if "." in canonical else canonical
            normalized.setdefault(attr, dict(cfg))

    if prefix_defaults:
        for stage_key in LLM_STAGE_KEYS.values():
            if stage_key in normalized:
                continue
            stage_lower = stage_key.lower()
            applied_cfg: StageOptions | None = None
            for prefix_key, default_cfg in prefix_defaults:
                if prefix_key is None:
                    applied_cfg = dict(default_cfg)
                    break
                if stage_lower.startswith(prefix_key):
                    applied_cfg = dict(default_cfg)
                    break
            if applied_cfg is None:
                continue
            normalized[stage_key] = applied_cfg
            attr = stage_key.split(".", 1)[1]
            normalized.setdefault(attr, dict(applied_cfg))

    return normalized


def _normalize_stage_identifier(value: str) -> Optional[str]:
    key = value.strip().lower()
    if not key:
        return None
    return _STAGE_ALIAS_LOOKUP.get(key)


@dataclass(frozen=True)
class StageProfile:
    stage_key: str
    label: str
    description: str
    min_context_tokens: int
    recommended_context_tokens: int
    target_chunk_tokens: int
    output_reserve_tokens: int
    resource_notes: str


ANALYZE_STAGE_PROFILES: dict[str, StageProfile] = {
    "analyze.context_builder": StageProfile(
        stage_key="analyze.context_builder",
        label="Context Builder",
        description="Prepares digestible transcript snippets and intake metadata.",
        min_context_tokens=4000,
        recommended_context_tokens=8000,
        target_chunk_tokens=40000,
        output_reserve_tokens=0,
        resource_notes="Runs locally (CPU).",
    ),
    "analyze.extract_outline": StageProfile(
        stage_key="analyze.extract_outline",
        label="Outline Extractor",
        description="Finds parties, issues, facts, and orders across the transcript.",
        min_context_tokens=8000,
        recommended_context_tokens=80000,
        target_chunk_tokens=40000,
        output_reserve_tokens=12000,
        resource_notes="Prefers 100k+ token context models for full hearings.",
    ),
    "analyze.build_timeline_seeds": StageProfile(
        stage_key="analyze.build_timeline_seeds",
        label="Timeline Seeding",
        description="Generates chronological event scaffolding for timeline view.",
        min_context_tokens=6000,
        recommended_context_tokens=60000,
        target_chunk_tokens=30000,
        output_reserve_tokens=6000,
        resource_notes="Heavier prompts; look for models with >=80k token windows.",
    ),
    "analyze.build_entity_hints": StageProfile(
        stage_key="analyze.build_entity_hints",
        label="Entity Mapper",
        description="Extracts people, organizations, and relationships with evidence.",
        min_context_tokens=6000,
        recommended_context_tokens=60000,
        target_chunk_tokens=30000,
        output_reserve_tokens=6000,
        resource_notes="Prefers large context for repeated mentions across the record.",
    ),
    "analyze.draft_markdown": StageProfile(
        stage_key="analyze.draft_markdown",
        label="Analysis Drafter",
        description="Produces the layered Markdown analysis and checklist.",
        min_context_tokens=8000,
        recommended_context_tokens=80000,
        target_chunk_tokens=50000,
        output_reserve_tokens=12000,
        resource_notes="Needs room for structured inputs; choose 100k token models when possible.",
    ),
    "analyze.qa_and_finalize": StageProfile(
        stage_key="analyze.qa_and_finalize",
        label="QA & Finalizer",
        description="Ensures required sections, hashes artifacts, and finalizes outputs.",
        min_context_tokens=4000,
        recommended_context_tokens=16000,
        target_chunk_tokens=10000,
        output_reserve_tokens=4000,
        resource_notes="Lightweight; smaller context models are acceptable.",
    ),
}


def _stage_profile(stage_key: str) -> StageProfile:
    return ANALYZE_STAGE_PROFILES.get(
        stage_key,
        StageProfile(
            stage_key=stage_key,
            label=stage_key,
            description="",
            min_context_tokens=2000,
            recommended_context_tokens=4000,
            target_chunk_tokens=4000,
            output_reserve_tokens=2000,
            resource_notes="",
        ),
    )


logger = logging.getLogger("udocket.analyze.agent")

def _load_llm_settings() -> LLMSettings:
    global _llm_settings_cache
    if _llm_settings_cache is None:
        _llm_settings_cache = load_llm_settings()
    return _llm_settings_cache


def _empty_options() -> dict[str, object]:
    return {}


@dataclass
class StageRuntime:
    stage_key: str
    providers: list[str]
    provider: str
    model: str
    client: Optional[ChatClient]
    max_output_tokens: int
    context_window_tokens: Optional[int]
    profile: StageProfile
    temperature: float
    options: dict[str, object] = field(default_factory=_empty_options)

    @property
    def primary_provider(self) -> str:
        if self.providers:
            return self.providers[0]
        if self.provider:
            return self.provider
        return "azure"


def _stage_error_message(
    stage_key: str,
    *,
    provider: Optional[str],
    model: Optional[str],
    reason: str,
) -> str:
    descriptor: list[str] = []
    if provider:
        if model:
            descriptor.append(f"provider '{provider}' model '{model}'")
        else:
            descriptor.append(f"provider '{provider}'")
    message = f"[{stage_key}] {reason}"
    if descriptor:
        message = f"{message} ({', '.join(descriptor)})"
    return (
        f"{message}. Review the LLM configuration in Organization Settings and run the live model test before retrying."
    )


PIPELINE_NODE_ORDER = [
    "input_discovery",
    "parse_transcript",
    "context_builder",
    "extract_outline",
    "build_timeline_seeds",
    "build_entity_hints",
    "draft_markdown",
    "qa_and_finalize",
    "write_ops_and_artifacts",
]


@dataclass
class AnalyzeConfig:
    language: str = "en-CA"
    temperature: float = DEFAULT_TEMPERATURE
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    debug: bool = False
    provider_chain: list[str] = field(
        default_factory=lambda: list(DEFAULT_PROVIDER_CHAIN)
    )
    max_prompt_segments: int = MAX_PROMPT_SEGMENTS
    max_prompt_chars: int = MAX_PROMPT_CHARS
    prompt_segments_override: Optional[int] = None
    prompt_chars_override: Optional[int] = None
    chars_per_token: float = DEFAULT_TOKENS_TO_CHAR_RATIO

    @classmethod
    def from_env(cls) -> "AnalyzeConfig":
        language = (os.getenv("LANGUAGE") or "en-CA").strip() or "en-CA"
        temperature = DEFAULT_TEMPERATURE
        max_tokens = DEFAULT_MAX_OUTPUT_TOKENS
        debug = os.getenv("DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}

        max_prompt_segments = MAX_PROMPT_SEGMENTS
        prompt_segments_override: Optional[int] = None

        max_prompt_chars = MAX_PROMPT_CHARS
        prompt_chars_override: Optional[int] = None

        chars_per_token = DEFAULT_TOKENS_TO_CHAR_RATIO

        providers = _normalize_providers(DEFAULT_PROVIDER_CHAIN)
        if not providers:
            providers = ["azure"]

        return cls(
            language=language,
            temperature=temperature,
            max_output_tokens=max_tokens,
            debug=debug,
            provider_chain=providers,
            max_prompt_segments=max_prompt_segments,
            max_prompt_chars=max_prompt_chars,
            prompt_segments_override=prompt_segments_override,
            prompt_chars_override=prompt_chars_override,
            chars_per_token=chars_per_token,
        )

    def stage_max_tokens_for(
        self,
        stage_key: str,
        model_limit: Optional[int],
        default_limit: Optional[int] = None,
    ) -> int:
        candidate = default_limit if default_limit and default_limit > 0 else self.max_output_tokens
        if not candidate or candidate <= 0:
            configured_default = DEFAULT_STAGE_TOKEN_LIMITS.get(stage_key)
            if configured_default is not None and configured_default > 0:
                candidate = configured_default
        if model_limit:
            candidate = min(candidate, model_limit) if candidate else model_limit
        if not candidate or candidate <= 0:
            candidate = model_limit if model_limit and model_limit > 0 else self.max_output_tokens
        return max(candidate, 1)


@dataclass
class AnalyzeResult:
    status: str
    summary_file: Path
    summary_markdown_file: Path
    outline_file: Optional[Path]
    timeline_seeds_file: Optional[Path]
    entity_hints_file: Optional[Path]
    case_brief_file: Optional[Path]
    words: int
    source_transcript: Path
    meta_json: Path
    audit_jsonl: Path
    provider_chain: list[str]


class AnalyzeAgent:
    def __init__(self, config: Optional[AnalyzeConfig] = None) -> None:
        self.config = config or AnalyzeConfig.from_env()
        self.logger = logger
        self._log_enabled = False
        self._log_level = logging.INFO
        enable_langgraph_debug_logging(force=self.config.debug)

    def stage_catalog(self) -> dict[str, StageCatalogEntry]:
        settings = _load_llm_settings()
        catalog: dict[str, StageCatalogEntry] = {}
        for stage_key, profile in ANALYZE_STAGE_PROFILES.items():
            eligible_models: list[StageModelInfo] = []
            for provider_name, provider in settings.providers.items():
                for model_name, model in provider.models.items():
                    context_tokens = model.context_window_tokens
                    if context_tokens and context_tokens < profile.min_context_tokens:
                        continue
                    eligible_models.append(
                        StageModelInfo(
                            provider=provider_name,
                            model=model_name,
                            context_window_tokens=context_tokens,
                            max_output_tokens=model.max_output_tokens,
                            deployment_env=model.deployment_env,
                        )
                    )
            recommended_models: list[StageModelInfo] = [
                entry
                for entry in eligible_models
                if entry["context_window_tokens"]
                and entry["context_window_tokens"] >= profile.recommended_context_tokens
            ]
            catalog[stage_key] = StageCatalogEntry(
                label=profile.label,
                description=profile.description,
                min_context_tokens=profile.min_context_tokens,
                recommended_context_tokens=profile.recommended_context_tokens,
                target_chunk_tokens=profile.target_chunk_tokens,
                output_reserve_tokens=profile.output_reserve_tokens,
                resource_notes=profile.resource_notes,
                recommended_models=recommended_models,
                eligible_models=eligible_models,
            )
        return catalog

    def _log(self, level: int, message: str, **meta: object) -> None:
        if not self._log_enabled:
            return
        details = " ".join(
            f"{key}={value}"
            for key, value in meta.items()
            if value is not None
        )
        full_message = message if not details else f"{message} | {details}"
        self.logger.log(level, full_message)

    def analyze(
        self,
        *,
        input: Optional[Path] = None,
        case_id: str,
        case_dir: Path,
        job_id: str,
        intake: Mapping[str, object] | None = None,
        transcript_hint: Mapping[str, object] | None = None,
        provider_chain: Sequence[str] | None = None,
        stage_map: Mapping[str, Mapping[str, object]] | None = None,
        provider_credentials: ProviderCredentials | None = None,
        progress_callback: Callable[[str, str, Mapping[str, object]], None]
        | None = None,
    ) -> AnalyzeResult:
        case_dir = Path(case_dir)
        state: dict[str, object] = {
            "case_id": case_id,
            "job_id": job_id,
            "case_dir": case_dir,
        }
        if input is not None:
            state["input_path"] = Path(input)

        self._log_enabled = (
            self.config.debug or self.logger.isEnabledFor(logging.DEBUG)
        )
        self._log_level = logging.INFO if self.config.debug else logging.DEBUG
        self._log(
            self._log_level,
            "analyze.start",
            case_id=case_id,
            job_id=job_id,
        )

        settings = _load_llm_settings()
        stage_map = _normalize_stage_map(stage_map)
        stage_overrides = _build_stage_override_index(stage_map)
        intake_mapping = intake or {}
        intake_data: dict[str, object] = {
            str(key): value for key, value in intake_mapping.items()
        }
        intake = intake_data
        transcript_hint_mapping = transcript_hint or {}
        transcript_hint_data: dict[str, object] = {
            str(key): value for key, value in transcript_hint_mapping.items()
        }
        transcript_hint = transcript_hint_data

        if provider_chain is None:
            derived_chain: list[str] = []
            for override in stage_overrides.values():
                for provider_name in override.providers:
                    if provider_name and provider_name not in derived_chain:
                        derived_chain.append(provider_name)
            provider_chain = derived_chain or list(self.config.provider_chain)
        provider_chain = _normalize_providers(provider_chain)
        if not provider_chain:
            provider_chain = list(DEFAULT_PROVIDER_CHAIN)

        provider_credentials = {
            str(key): dict(value)
            for key, value in (provider_credentials or {}).items()
        }

        stage_runtimes: dict[str, StageRuntime] = {}
        provider_sequence: list[str] = []

        for _stage_attr, stage_key in LLM_STAGE_KEYS.items():
            stage_profile = _stage_profile(stage_key)
            assignment = settings.stage(stage_key)
            providers = _normalize_providers(
                assignment.providers if assignment and assignment.providers else provider_chain
            )
            if not providers:
                providers = list(provider_chain)

            if not providers:
                raise RuntimeError(
                    _stage_error_message(
                        stage_key,
                        provider=None,
                        model=None,
                        reason="No provider configured",
                    )
                )

            preferred_model = (
                str(assignment.model).strip()
                if assignment and assignment.model
                else ""
            )
            options: dict[str, object] = {}
            if assignment and assignment.options:
                options.update(dict(assignment.options))

            override_max_tokens = None
            stage_override = stage_overrides.get(stage_key)
            if stage_override is not None:
                if stage_override.providers:
                    providers = list(stage_override.providers)
                if stage_override.model:
                    preferred_model = stage_override.model
                if stage_override.options:
                    options.update(stage_override.options)
                if stage_override.max_tokens is not None:
                    override_max_tokens = stage_override.max_tokens

            requires_chat = stage_key != "analyze.context_builder"
            provider_name = providers[0]
            credential_payload = provider_credentials.get(provider_name)
            provider_meta = settings.provider(provider_name)

            chat_client: Optional[ChatClient] = None
            model_meta = None

            if requires_chat:
                if provider_meta is None:
                    raise RuntimeError(
                        _stage_error_message(
                            stage_key,
                            provider=provider_name,
                            model=None,
                            reason="Provider is not configured",
                        )
                    )
                if not preferred_model:
                    raise RuntimeError(
                        _stage_error_message(
                            stage_key,
                            provider=provider_name,
                            model=None,
                            reason="No model configured",
                        )
                    )
                model_meta = provider_meta.models.get(preferred_model)
                if model_meta is None:
                    raise RuntimeError(
                        _stage_error_message(
                            stage_key,
                            provider=provider_name,
                            model=preferred_model,
                            reason="Model is not registered",
                        )
                    )
                try:
                    credential_payload_json = (
                        coerce_json_object(credential_payload)
                        if credential_payload is not None
                        else None
                    )
                    options_json = coerce_json_object(options)
                    runtime_cfg = build_provider_runtime_config(
                        provider=provider_meta,
                        model_name=preferred_model,
                        credential_payload=credential_payload_json,
                        options=options_json,
                    )
                except ChatClientError as exc:  # pragma: no cover - configuration errors
                    self._log(
                        logging.ERROR,
                        "stage.config.error",
                        stage=stage_key,
                        provider=provider_name,
                        model=preferred_model,
                        error=str(exc),
                    )
                    raise RuntimeError(
                        _stage_error_message(
                            stage_key,
                            provider=provider_name,
                            model=preferred_model,
                            reason=f"Unable to configure provider: {exc}",
                        )
                    ) from exc

                try:
                    chat_client = build_chat_client(provider_runtime=runtime_cfg)
                    model_meta = runtime_cfg.model or model_meta
                except ChatClientError as exc:  # pragma: no cover - runtime errors
                    self._log(
                        logging.ERROR,
                        "stage.client.error",
                        stage=stage_key,
                        provider=provider_name,
                        model=preferred_model,
                        error=str(exc),
                    )
                    raise RuntimeError(
                        _stage_error_message(
                            stage_key,
                            provider=provider_name,
                            model=preferred_model,
                            reason=f"Provider rejected the connection: {exc}",
                        )
                    ) from exc
            else:
                if provider_meta and preferred_model:
                    model_meta = provider_meta.models.get(preferred_model)

            stage_max_tokens_base = (
                model_meta.max_output_tokens
                if model_meta and model_meta.max_output_tokens
                else self.config.max_output_tokens
            )
            if override_max_tokens is not None:
                stage_max_tokens_base = override_max_tokens
            stage_max_tokens = self.config.stage_max_tokens_for(
                stage_key,
                model_meta.max_output_tokens if model_meta else None,
                default_limit=stage_max_tokens_base,
            )
            stage_temperature = (
                model_meta.default_temperature
                if model_meta and model_meta.default_temperature is not None
                else self.config.temperature
            )
            temperature_override = options.get("temperature")
            if temperature_override is not None:
                stage_temperature = _coerce_float(temperature_override, stage_temperature)

            context_window_tokens = (
                model_meta.context_window_tokens if model_meta and model_meta.context_window_tokens else None
            )

            runtime = StageRuntime(
                stage_key=stage_key,
                providers=providers,
                provider=provider_name,
                model=preferred_model,
                client=chat_client,
                max_output_tokens=stage_max_tokens or self.config.max_output_tokens,
                context_window_tokens=context_window_tokens,
                profile=stage_profile,
                temperature=stage_temperature,
                options=dict(options),
            )

            stage_runtimes[stage_key] = runtime

            if provider_name not in provider_sequence:
                provider_sequence.append(provider_name)

            self._log(
                self._log_level,
                "stage.configured",
                stage=stage_key,
                providers=runtime.providers,
                model=runtime.model,
                client_available=bool(runtime.client),
            )

        for stage_key, runtime in stage_runtimes.items():
            client = runtime.client
            if client is None:
                continue

            def _raise_error(message: str, *, _stage: str = stage_key, _runtime: StageRuntime = runtime) -> Exception:
                return RuntimeError(
                    _stage_error_message(
                        _stage,
                        provider=_runtime.provider,
                        model=_runtime.model,
                        reason=message,
                    )
                )

            ensure_llm_client_health(
                client,
                stage=stage_key,
                provider=runtime.provider,
                model=runtime.model,
                logger=self.logger,
                raise_error=_raise_error,
            )

        pipeline = AnalyzePipeline(
            case_id=case_id,
            job_id=job_id,
            case_dir=case_dir,
            intake=intake,
            transcript_hint=transcript_hint,
            config=self.config,
            resolve_transcript=self._resolve_transcript,
            build_context=self._build_context,
            provider_chain=provider_sequence,
            stage_runtimes=stage_runtimes,
            default_temperature=self.config.temperature,
            logger=self.logger,
            progress_callback=self._build_progress_dispatch(
                progress_callback, case_id, job_id
            ),
        )

        pipeline.emit_pipeline_event("start", provider_chain=provider_sequence)
        final_state = self._execute_pipeline(pipeline, state)
        final_outputs = final_state.get("final_outputs")
        if not isinstance(final_outputs, FinalizedOutputs):
            raise RuntimeError("Analyze pipeline did not produce outputs")

        transcript_path = final_state.get("transcript_path")
        if not isinstance(transcript_path, Path):
            input_path_obj = state.get("input_path")
            input_path = input_path_obj if isinstance(input_path_obj, Path) else None
            transcript_path = self._resolve_transcript(
                input_path, case_dir
            )

        status_value = final_state.get("status", "ok")
        status = status_value if isinstance(status_value, str) else "ok"

        pipeline.emit_pipeline_event(
            "complete",
            status=status,
        )
        self._log(
            self._log_level,
            "analyze.completed",
            status=status,
            summary=str(final_outputs.summary_path),
            outline=str(final_outputs.outline_path),
        )
        return AnalyzeResult(
            status=status,
            summary_file=final_outputs.summary_path,
            summary_markdown_file=final_outputs.summary_markdown_path,
            outline_file=final_outputs.outline_path,
            timeline_seeds_file=final_outputs.timeline_seed_path,
            entity_hints_file=final_outputs.entity_hint_path,
            case_brief_file=final_outputs.case_brief_path,
            words=final_outputs.words,
            source_transcript=transcript_path,
            meta_json=final_outputs.meta_path,
            audit_jsonl=final_outputs.audit_path,
            provider_chain=list(final_outputs.provider_chain),
        )

    def _execute_pipeline(
        self, pipeline: AnalyzePipeline, state: Mapping[str, object]
    ) -> dict[str, object]:
        current_state: dict[str, object] = dict(state)
        graph = None
        try:
            graph = build_analyze_graph(pipeline)
        except RuntimeError:
            graph = None
        if graph is not None:
            self._log(logging.DEBUG, "langgraph.invoke.start", entry=graph.entry)
            graph_result = graph.invoke(current_state)
            self._log(
                logging.DEBUG,
                "langgraph.invoke.complete",
                state_keys=list(graph_result.keys()),
            )
            return dict(graph_result)
        for node_name in PIPELINE_NODE_ORDER:
            node = getattr(pipeline, node_name)
            current_state = node(current_state)
        return dict(current_state)

    def _build_progress_dispatch(
        self,
        external_callback: Callable[[str, str, Mapping[str, object]], None]
        | None,
        case_id: str,
        job_id: str,
    ) -> Callable[[str, str, Mapping[str, object]], None]:
        def dispatch(stage: str, event: str, payload: Mapping[str, object]) -> None:
            log_level = logging.INFO if self.config.debug else logging.DEBUG
            self._log(log_level, f"stage.{stage}.{event}", **payload)
            if external_callback is not None:
                try:
                    external_callback(stage, event, dict(payload))
                except Exception:
                    self.logger.exception(
                        "External progress callback failed",
                        extra={
                            "stage": stage,
                            "event": event,
                            "job_id": job_id,
                            "case_id": case_id,
                        },
                    )

        return dispatch

    def _resolve_transcript(
        self, input_path: Optional[Path], case_dir: Path
    ) -> Path:
        if input_path:
            resolved = Path(input_path)
            if not resolved.exists():
                raise FileNotFoundError(f"Transcript not found at {resolved}")
            return resolved
        transcript_dir = case_dir / "transcript"
        if not transcript_dir.exists():
            raise FileNotFoundError(
                f"No transcript directory at {transcript_dir}"
            )
        candidates = sorted(
            (
                p
                for p in transcript_dir.glob("*__transcript.txt")
                if p.is_file()
            ),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            raise FileNotFoundError("No transcript files found for case")
        return candidates[0]

    def _build_context(
        self, parse: TranscriptParse, intake: Mapping[str, object]
    ) -> str:
        snippets: list[str] = []
        chars = 0
        segment_limit = getattr(self.config, "max_prompt_segments", MAX_PROMPT_SEGMENTS)
        char_limit = getattr(self.config, "max_prompt_chars", MAX_PROMPT_CHARS)
        unlimited_segments = segment_limit == 0
        unlimited_chars = char_limit == 0
        for seg in parse.segments:
            text = seg.text.strip()
            if not text:
                continue
            prefix = ""
            if seg.ts is not None:
                minutes = int(seg.ts // 60)
                seconds = int(seg.ts % 60)
                speaker = seg.speaker or "SPK"
                prefix = f"[{minutes:02d}:{seconds:02d}] {speaker}: "
            line = prefix + text
            snippets.append(line)
            chars += len(line)
            if (
                (not unlimited_segments and len(snippets) >= segment_limit)
                or (not unlimited_chars and chars >= char_limit)
            ):
                break
        context = "\n".join(snippets)
        if intake.get("court_case_number"):
            context = f"Case number: {intake['court_case_number']}\n" + context
        return context


__all__ = [
    "AnalyzeAgent",
    "AnalyzeConfig",
    "AnalyzeResult",
    "parse_transcript",
    "TranscriptParse",
    "TranscriptSegment",
    "DISALLOWED_PROVIDERS",
]
