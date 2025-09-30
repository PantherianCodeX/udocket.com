from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, cast

from .common import (
    AzureChatClient,
    AzureClientConfig,
    parse_transcript,
    TranscriptParse,
)
from .common.azure_client import CANADIAN_REGIONS
from .common.io import TranscriptSegment  # re-export for legacy imports
from .langgraph_orchestrator import build_summarize_graph, enable_langgraph_debug_logging
from .summarize.utils import FinalizedOutputs, SummarizePipeline
from ..llm import LLMSettings, load_llm_settings

BASE_DIR = Path(__file__).resolve().parents[3]
SUMMARIZE_DEFAULTS_PATH = BASE_DIR / "config" / "summarize_defaults.json"


@lru_cache(maxsize=1)
def load_summarize_defaults() -> Dict[str, Any]:
    try:
        payload = json.loads(SUMMARIZE_DEFAULTS_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def summarize_defaults() -> Dict[str, Any]:
    return dict(load_summarize_defaults())


_DEFAULTS = load_summarize_defaults()

MAX_PROMPT_SEGMENTS = int(_DEFAULTS.get("max_prompt_segments", 250))
MAX_PROMPT_CHARS = int(_DEFAULTS.get("max_prompt_chars", 32000))
DEFAULT_TOKENS_TO_CHAR_RATIO = float(_DEFAULTS.get("chars_per_token", 4.0))
DEFAULT_TEMPERATURE = float(_DEFAULTS.get("temperature", 1.0))
DEFAULT_MAX_OUTPUT_TOKENS = int(_DEFAULTS.get("max_output_tokens", 24000))

_DEFAULT_CHAIN = [
    str(value).strip().lower()
    for value in _DEFAULTS.get("default_provider_chain", ["azure"])
    if str(value).strip()
]
DEFAULT_PROVIDER_CHAIN: List[str] = _DEFAULT_CHAIN or ["azure"]

_STAGE_LIMITS_DEFAULT = _DEFAULTS.get("stage_token_limits") or {}
DEFAULT_STAGE_TOKEN_LIMITS: Dict[str, int] = {
    "summarize.extract_outline": int(_STAGE_LIMITS_DEFAULT.get("summarize.extract_outline", 12000)),
    "summarize.build_timeline_seeds": int(_STAGE_LIMITS_DEFAULT.get("summarize.build_timeline_seeds", 8000)),
    "summarize.build_entity_hints": int(_STAGE_LIMITS_DEFAULT.get("summarize.build_entity_hints", 8000)),
    "summarize.draft_markdown": int(_STAGE_LIMITS_DEFAULT.get("summarize.draft_markdown", 12000)),
    "summarize.qa_and_finalize": int(_STAGE_LIMITS_DEFAULT.get("summarize.qa_and_finalize", 6000)),
}
LLM_STAGE_KEYS = {
    "context_builder": "summarize.context_builder",
    "extract_outline": "summarize.extract_outline",
    "build_timeline_seeds": "summarize.build_timeline_seeds",
    "build_entity_hints": "summarize.build_entity_hints",
    "draft_markdown": "summarize.draft_markdown",
    "qa_and_finalize": "summarize.qa_and_finalize",
}
_llm_settings_cache: Optional[LLMSettings] = None

_STAGE_ALIAS_LOOKUP: Dict[str, str] = {}
for _attr, _stage_key in LLM_STAGE_KEYS.items():
    _STAGE_ALIAS_LOOKUP[_attr.lower()] = _stage_key
    _STAGE_ALIAS_LOOKUP[_stage_key.lower()] = _stage_key
    if _stage_key.startswith("summarize."):
        _STAGE_ALIAS_LOOKUP[_stage_key.split(".", 1)[1].lower()] = _stage_key


DISALLOWED_PROVIDERS: set[str] = set()


def _normalize_stage_map(
    stage_map: Optional[Dict[str, Dict[str, Any]]],
) -> Dict[str, Dict[str, Any]]:
    if not stage_map:
        return {}
    normalized: Dict[str, Dict[str, Any]] = {}
    for key, value in stage_map.items():
        canonical = _normalize_stage_identifier(str(key))
        if not canonical:
            canonical = key if key in LLM_STAGE_KEYS.values() else None
        if not canonical:
            continue
        if not isinstance(value, dict):
            continue
        normalized[canonical] = {str(k): v for k, v in value.items()}
    return normalized


def _normalize_stage_identifier(value: str) -> Optional[str]:
    key = value.strip().lower()
    if not key:
        return None
    return _STAGE_ALIAS_LOOKUP.get(key)


def _parse_stage_mapping(
    raw: str,
    value_parser: Callable[[str], Optional[Any]],
) -> Dict[str, Any]:
    if not raw:
        return {}

    mapping: Dict[str, Any] = {}
    entries: List[tuple[str, str]] = []

    payload: Any = None
    try:
        payload = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        payload = None

    if isinstance(payload, dict):
        entries.extend((str(key), str(value)) for key, value in payload.items())
    elif isinstance(payload, list):
        for item in payload:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                continue
            stage_name, stage_value = item
            entries.append((str(stage_name), str(stage_value)))

    if not entries:
        parts = [part.strip() for part in raw.split(",") if part.strip()]
        for part in parts:
            if "=" in part:
                stage_name, stage_value = part.split("=", 1)
            elif ":" in part:
                stage_name, stage_value = part.split(":", 1)
            else:
                continue
            entries.append((stage_name.strip(), stage_value.strip()))

    for stage_name, stage_value in entries:
        if not stage_name:
            continue
        normalized = None
        if stage_name in {"*", "default"}:
            normalized = "*"
        else:
            normalized = _normalize_stage_identifier(stage_name)
        if not normalized and stage_name != "*":
            continue
        parsed_value = value_parser(stage_value)
        if parsed_value is None:
            continue
        target_key = normalized if normalized else "*"
        mapping[target_key] = parsed_value
    return mapping


def _parse_positive_int(value: str) -> Optional[int]:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def _parse_non_empty_str(value: str) -> Optional[str]:
    string_value = str(value).strip()
    return string_value or None


def _normalize_providers(values: Sequence[str]) -> List[str]:
    seen: set[str] = set()
    normalized: List[str] = []
    for raw in values:
        name = (raw or "").strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized


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


SUMMARIZE_STAGE_PROFILES: Dict[str, StageProfile] = {
    "summarize.context_builder": StageProfile(
        stage_key="summarize.context_builder",
        label="Context Builder",
        description="Prepares digestible transcript snippets and intake metadata.",
        min_context_tokens=4000,
        recommended_context_tokens=8000,
        target_chunk_tokens=40000,
        output_reserve_tokens=0,
        resource_notes="Runs locally (CPU).",
    ),
    "summarize.extract_outline": StageProfile(
        stage_key="summarize.extract_outline",
        label="Outline Extractor",
        description="Finds parties, issues, facts, and orders across the transcript.",
        min_context_tokens=8000,
        recommended_context_tokens=80000,
        target_chunk_tokens=40000,
        output_reserve_tokens=12000,
        resource_notes="Prefers 100k+ token context models for full hearings.",
    ),
    "summarize.build_timeline_seeds": StageProfile(
        stage_key="summarize.build_timeline_seeds",
        label="Timeline Seeding",
        description="Generates chronological event scaffolding for timeline view.",
        min_context_tokens=6000,
        recommended_context_tokens=60000,
        target_chunk_tokens=30000,
        output_reserve_tokens=6000,
        resource_notes="Heavier prompts; look for models with >=80k token windows.",
    ),
    "summarize.build_entity_hints": StageProfile(
        stage_key="summarize.build_entity_hints",
        label="Entity Mapper",
        description="Extracts people, organizations, and relationships with evidence.",
        min_context_tokens=6000,
        recommended_context_tokens=60000,
        target_chunk_tokens=30000,
        output_reserve_tokens=6000,
        resource_notes="Prefers large context for repeated mentions across the record.",
    ),
    "summarize.draft_markdown": StageProfile(
        stage_key="summarize.draft_markdown",
        label="Summary Drafter",
        description="Produces the layered Markdown summary and checklist.",
        min_context_tokens=8000,
        recommended_context_tokens=80000,
        target_chunk_tokens=50000,
        output_reserve_tokens=12000,
        resource_notes="Needs room for structured inputs; choose 100k token models when possible.",
    ),
    "summarize.qa_and_finalize": StageProfile(
        stage_key="summarize.qa_and_finalize",
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
    return SUMMARIZE_STAGE_PROFILES.get(
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


logger = logging.getLogger("udocket.summarize.agent")


def _endpoint_is_canadian(endpoint: str) -> bool:
    endpoint_lower = endpoint.lower()
    return any(region in endpoint_lower for region in CANADIAN_REGIONS)


def _load_llm_settings() -> LLMSettings:
    global _llm_settings_cache
    if _llm_settings_cache is None:
        _llm_settings_cache = load_llm_settings()
    return _llm_settings_cache


@dataclass
class StageRuntime:
    stage_key: str
    providers: List[str]
    model: str
    azure_client: Optional[AzureChatClient]
    max_output_tokens: int
    context_window_tokens: Optional[int]
    profile: StageProfile
    temperature: float

    @property
    def primary_provider(self) -> str:
        return self.providers[0] if self.providers else "azure"


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
class SummarizeConfig:
    azure_openai_endpoint: str = ""
    azure_openai_key: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = "2024-10-21"
    language: str = "en-CA"
    temperature: float = DEFAULT_TEMPERATURE
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    debug: bool = False
    provider_chain: List[str] = field(
        default_factory=lambda: list(DEFAULT_PROVIDER_CHAIN)
    )
    max_prompt_segments: int = MAX_PROMPT_SEGMENTS
    max_prompt_chars: int = MAX_PROMPT_CHARS
    prompt_segments_override: Optional[int] = None
    prompt_chars_override: Optional[int] = None
    default_stage_model: Optional[str] = None
    stage_model_overrides: Dict[str, str] = field(default_factory=dict)
    stage_max_output_tokens: Dict[str, int] = field(default_factory=dict)
    chars_per_token: float = DEFAULT_TOKENS_TO_CHAR_RATIO

    @classmethod
    def from_env(cls) -> "SummarizeConfig":
        endpoint = (os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip()
        key = (os.getenv("AZURE_OPENAI_API_KEY") or "").strip()
        deployment = (os.getenv("AZURE_OPENAI_DEPLOYMENT") or "").strip()
        api_version = (
            os.getenv("AZURE_OPENAI_API_VERSION") or "2024-10-21"
        ).strip()
        language = (os.getenv("LANGUAGE") or "en-CA").strip() or "en-CA"
        temperature = DEFAULT_TEMPERATURE
        max_tokens = DEFAULT_MAX_OUTPUT_TOKENS
        debug = os.getenv("DEBUG", "0").strip() == "1"

        allow_non_ca_endpoint = (
            os.getenv("SUMMARY_ALLOW_NON_CA_ENDPOINT", "0").strip() == "1"
        )
        if endpoint and not allow_non_ca_endpoint and not _endpoint_is_canadian(endpoint):
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT must target canadacentral or canadaeast"
            )

        max_prompt_segments = MAX_PROMPT_SEGMENTS
        prompt_segments_override: Optional[int] = None

        max_prompt_chars = MAX_PROMPT_CHARS
        prompt_chars_override: Optional[int] = None

        default_stage_model = None
        stage_model_overrides: Dict[str, str] = {}
        stage_max_output_tokens: Dict[str, int] = {}
        chars_per_token = DEFAULT_TOKENS_TO_CHAR_RATIO

        providers = _normalize_providers(DEFAULT_PROVIDER_CHAIN)
        if "azure" not in providers:
            logger.warning(
                "Summarize currently requires Azure; prepending azure to provider chain",
                extra={"providers": providers},
            )
            providers = ["azure"] + [name for name in providers if name != "azure"]
        if not providers:
            providers = ["azure"]

        return cls(
            azure_openai_endpoint=endpoint,
            azure_openai_key=key,
            azure_openai_deployment=deployment,
            azure_openai_api_version=api_version,
            language=language,
            temperature=temperature,
            max_output_tokens=max_tokens,
            debug=debug,
            provider_chain=providers,
            max_prompt_segments=max_prompt_segments,
            max_prompt_chars=max_prompt_chars,
            prompt_segments_override=prompt_segments_override,
            prompt_chars_override=prompt_chars_override,
            default_stage_model=default_stage_model,
            stage_model_overrides=stage_model_overrides,
            stage_max_output_tokens=stage_max_output_tokens,
            chars_per_token=chars_per_token,
        )


    @property
    def azure_enabled(self) -> bool:
        if "azure" not in self.provider_chain:
            return False
        return bool(
            self.azure_openai_endpoint
            and self.azure_openai_key
            and self.azure_openai_deployment
        )

    def stage_model_for(self, stage_key: str) -> Optional[str]:
        override = self.stage_model_overrides.get(stage_key)
        if override:
            return override
        return self.stage_model_overrides.get("*") or self.default_stage_model

    def stage_max_tokens_for(
        self,
        stage_key: str,
        model_limit: Optional[int],
        fallback: Optional[int] = None,
    ) -> int:
        candidate = self.max_output_tokens
        override = self.stage_max_output_tokens.get(stage_key)
        if override is None:
            override = self.stage_max_output_tokens.get("*")
        if override is not None and override > 0:
            candidate = override
        elif fallback is not None and fallback > 0:
            candidate = fallback
        else:
            default_limit = DEFAULT_STAGE_TOKEN_LIMITS.get(stage_key)
            if default_limit is not None and default_limit > 0:
                candidate = default_limit
        if model_limit:
            candidate = min(candidate, model_limit) if candidate else model_limit
        if not candidate or candidate <= 0:
            candidate = model_limit if model_limit and model_limit > 0 else self.max_output_tokens
        return max(candidate, 1)

    @property
    def azure_region(self) -> Optional[str]:
        if not self.azure_openai_endpoint:
            return None
        endpoint_lower = self.azure_openai_endpoint.lower()
        if "canadacentral" in endpoint_lower:
            return "canadacentral"
        if "canadaeast" in endpoint_lower:
            return "canadaeast"
        return None

    def azure_client_config(self) -> Optional[AzureClientConfig]:
        if not self.azure_enabled:
            return None
        allow_non_ca_endpoint = (
            os.getenv("SUMMARY_ALLOW_NON_CA_ENDPOINT", "0").strip() == "1"
        )
        return AzureClientConfig(
            endpoint=self.azure_openai_endpoint,
            key=self.azure_openai_key,
            deployment=self.azure_openai_deployment,
            api_version=self.azure_openai_api_version,
            allow_non_ca_region=allow_non_ca_endpoint,
        )

    def azure_client_config_for(
        self, deployment: Optional[str]
    ) -> Optional[AzureClientConfig]:
        cfg = self.azure_client_config()
        if cfg is None:
            return None
        if deployment:
            cfg.deployment = deployment
        return cfg


@dataclass
class SummarizeResult:
    status: str
    summary_file: Path
    outline_file: Optional[Path]
    timeline_seeds_file: Optional[Path]
    entity_hints_file: Optional[Path]
    case_brief_file: Optional[Path]
    words: int
    source_transcript: Path
    meta_json: Path
    audit_jsonl: Path
    provider_chain: List[str]


class SummarizeAgent:
    def __init__(self, config: Optional[SummarizeConfig] = None) -> None:
        self.config = config or SummarizeConfig.from_env()
        self.logger = logger
        self._log_enabled = False
        self._log_level = logging.INFO
        enable_langgraph_debug_logging(force=self.config.debug)

    def stage_catalog(self) -> Dict[str, Any]:
        settings = _load_llm_settings()
        catalog: Dict[str, Any] = {}
        for stage_key, profile in SUMMARIZE_STAGE_PROFILES.items():
            eligible_models: List[Dict[str, Any]] = []
            for provider_name, provider in settings.providers.items():
                for model_name, model in provider.models.items():
                    context_tokens = model.context_window_tokens
                    if context_tokens and context_tokens < profile.min_context_tokens:
                        continue
                    eligible_models.append(
                        {
                            "provider": provider_name,
                            "model": model_name,
                            "context_window_tokens": context_tokens,
                            "max_output_tokens": model.max_output_tokens,
                            "deployment_env": model.deployment_env,
                        }
                    )
            recommended_models = [
                entry
                for entry in eligible_models
                if entry["context_window_tokens"]
                and entry["context_window_tokens"] >= profile.recommended_context_tokens
            ]
            catalog[stage_key] = {
                "label": profile.label,
                "description": profile.description,
                "min_context_tokens": profile.min_context_tokens,
                "recommended_context_tokens": profile.recommended_context_tokens,
                "target_chunk_tokens": profile.target_chunk_tokens,
                "output_reserve_tokens": profile.output_reserve_tokens,
                "resource_notes": profile.resource_notes,
                "recommended_models": recommended_models,
                "eligible_models": eligible_models,
            }
        return catalog

    def _log(self, level: int, message: str, **meta: Any) -> None:
        if not self._log_enabled:
            return
        details = " ".join(
            f"{key}={value}"
            for key, value in meta.items()
            if value is not None
        )
        full_message = message if not details else f"{message} | {details}"
        self.logger.log(level, full_message)

    def summarize(
        self,
        *,
        input: Optional[Path] = None,
        case_id: str,
        case_dir: Path,
        job_id: str,
        intake: Optional[Dict[str, Any]] = None,
        transcript_hint: Optional[Dict[str, Any]] = None,
        provider_chain: Optional[List[str]] = None,
        stage_map: Optional[Dict[str, Dict[str, Any]]] = None,
        progress_callback: Optional[
            Callable[[str, str, Dict[str, Any]], None]
        ] = None,
    ) -> SummarizeResult:
        case_dir = Path(case_dir)
        state: Dict[str, Any] = {
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
            "summarize.start",
            case_id=case_id,
            job_id=job_id,
        )

        settings = _load_llm_settings()
        stage_map = _normalize_stage_map(stage_map)
        intake = dict(intake or {})

        if provider_chain is None:
            derived_chain: List[str] = []
            for config in stage_map.values():
                provider_value = config.get("provider")
                providers_value = config.get("providers")
                if isinstance(providers_value, list):
                    for entry in providers_value:
                        name = str(entry or "").strip().lower()
                        if name and name not in derived_chain:
                            derived_chain.append(name)
                elif isinstance(provider_value, str):
                    name = provider_value.strip().lower()
                    if name and name not in derived_chain:
                        derived_chain.append(name)
            provider_chain = derived_chain or list(self.config.provider_chain)
        provider_chain = _normalize_providers(provider_chain)
        if "azure" not in provider_chain:
            logger.warning(
                "Summarize currently requires Azure; prepending azure to provider chain",
                extra={"provider_chain": provider_chain},
            )
            provider_chain = ["azure"] + [value for value in provider_chain if value != "azure"]
        if not provider_chain:
            provider_chain = list(DEFAULT_PROVIDER_CHAIN)

        azure_enabled = self.config.azure_enabled
        if not azure_enabled:
            missing_env: List[str] = []
            if not self.config.azure_openai_endpoint:
                missing_env.append("AZURE_OPENAI_ENDPOINT")
            if not self.config.azure_openai_key:
                missing_env.append("AZURE_OPENAI_API_KEY")
            if not self.config.azure_openai_deployment:
                missing_env.append("AZURE_OPENAI_DEPLOYMENT")
            details = ", ".join(missing_env) if missing_env else "unknown"
            # TODO(multi-provider): allow non-Azure providers when chat abstractions land.
            raise RuntimeError(
                f"Azure OpenAI configuration is required for summarization (missing: {details})"
            )
        stage_runtimes: Dict[str, StageRuntime] = {}
        provider_sequence: List[str] = []

        azure_provider_meta = settings.provider("azure")

        for stage_attr, stage_key in LLM_STAGE_KEYS.items():
            stage_profile = _stage_profile(stage_key)
            assignment = settings.stage(stage_key)
            providers = _normalize_providers(
                assignment.providers if assignment and assignment.providers else provider_chain
            )
            if "azure" not in providers:
                self.logger.debug(
                    "azure provider inserted for stage",
                    extra={"stage": stage_key, "providers": providers},
                )
                providers = ["azure"] + [value for value in providers if value != "azure"]
            if not providers:
                providers = list(DEFAULT_PROVIDER_CHAIN)

            model = (
                assignment.model
                if assignment and assignment.model
                else (providers[0] if providers else "azure")
            )
            options = dict(assignment.options) if assignment else {}
            stage_config = stage_map.get(stage_key) or stage_map.get(stage_attr)
            override_max_tokens = None
            if stage_config:
                override_providers: Optional[List[str]] = None
                if isinstance(stage_config.get("providers"), list):
                    override_providers = [str(value) for value in stage_config["providers"]]
                elif stage_config.get("provider"):
                    override_providers = [str(stage_config["provider"])]
                if override_providers is not None:
                    override_normalized = _normalize_providers(override_providers)
                    if "azure" not in override_normalized:
                        override_normalized = ["azure"] + [p for p in override_normalized if p != "azure"]
                    if override_normalized:
                        providers = override_normalized
                if stage_config.get("model"):
                    model = str(stage_config["model"])
                stage_options = stage_config.get("options")
                if isinstance(stage_options, dict):
                    options.update({str(key): str(value) for key, value in stage_options.items()})
                max_tokens_override = stage_config.get("max_tokens")
                if isinstance(max_tokens_override, (int, float, str)):
                    try:
                        override_max_tokens = max(1, int(float(str(max_tokens_override))))
                    except (TypeError, ValueError):
                        override_max_tokens = None

            config_model_override = self.config.stage_model_for(stage_key)
            if config_model_override:
                model = config_model_override

            provider_meta = settings.provider(providers[0]) if providers else None
            if provider_meta is None and "azure" in providers and azure_provider_meta:
                provider_meta = azure_provider_meta
            model_meta = (
                provider_meta.models.get(model)
                if provider_meta and model in provider_meta.models
                else None
            )

            deployment = options.get("azure_deployment") if options else None
            if not deployment and model_meta and model_meta.deployment_env:
                deployment = os.getenv(model_meta.deployment_env)

            azure_client: Optional[AzureChatClient] = None
            if "azure" in providers:
                cfg = self.config.azure_client_config_for(deployment)
                if cfg:
                    azure_client = AzureChatClient(cfg)

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
                stage_max_tokens_base,
            )
            stage_temperature = (
                model_meta.default_temperature
                if model_meta and model_meta.default_temperature is not None
                else self.config.temperature
            )
            if options:
                temp_value = options.get("temperature")
                if temp_value is not None:
                    try:
                        stage_temperature = float(temp_value)
                    except (TypeError, ValueError):
                        pass

            context_window_tokens = None
            if model_meta and model_meta.context_window_tokens:
                context_window_tokens = model_meta.context_window_tokens

            runtime = StageRuntime(
                stage_key=stage_key,
                providers=providers,
                model=model,
                azure_client=azure_client,
                max_output_tokens=stage_max_tokens
                or self.config.max_output_tokens,
                context_window_tokens=context_window_tokens,
                profile=stage_profile,
                temperature=stage_temperature,
            )
            stage_runtimes[stage_key] = runtime

            for provider in providers:
                if provider not in provider_sequence:
                    provider_sequence.append(provider)

            self._log(
                self._log_level,
                "stage.configured",
                stage=stage_key,
                providers=providers,
                model=model,
                azure_client=bool(azure_client),
            )

        pipeline = SummarizePipeline(
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
            raise RuntimeError("Summarize pipeline did not produce outputs")

        transcript_path = final_state.get("transcript_path")
        if not isinstance(transcript_path, Path):
            transcript_path = self._resolve_transcript(
                state.get("input_path"), case_dir
            )

        pipeline.emit_pipeline_event(
            "complete",
            status=final_state.get("status", "ok"),
        )
        self._log(
            self._log_level,
            "summarize.completed",
            status=final_state.get("status", "ok"),
            summary=str(final_outputs.summary_path),
            outline=str(final_outputs.outline_path),
        )
        return SummarizeResult(
            status=final_state.get("status", "ok"),
            summary_file=final_outputs.summary_path,
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
        self, pipeline: SummarizePipeline, state: Dict[str, Any]
    ) -> Dict[str, Any]:
        current_state: Dict[str, Any] = dict(state)
        graph = None
        try:
            graph = build_summarize_graph(pipeline)
        except RuntimeError:
            graph = None
        if graph is not None:
            self._log(logging.DEBUG, "langgraph.invoke.start", entry=graph.entry)
            graph_result = graph.invoke(current_state)
            self._log(logging.DEBUG, "langgraph.invoke.complete", state_keys=list(graph_result.keys()))
            return dict(graph_result)
        for node_name in PIPELINE_NODE_ORDER:
            node = getattr(pipeline, node_name)
            current_state = node(current_state)
        return dict(current_state)

    def _build_progress_dispatch(
        self,
        external_callback: Optional[
            Callable[[str, str, Dict[str, Any]], None]
        ],
        case_id: str,
        job_id: str,
    ) -> Callable[[str, str, Dict[str, Any]], None]:
        def dispatch(stage: str, event: str, payload: Dict[str, Any]) -> None:
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
        self, parse: TranscriptParse, intake: Dict[str, Any]
    ) -> str:
        snippets: List[str] = []
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
    "SummarizeAgent",
    "SummarizeConfig",
    "SummarizeResult",
    "parse_transcript",
    "TranscriptParse",
    "TranscriptSegment",
    "DISALLOWED_PROVIDERS",
]
