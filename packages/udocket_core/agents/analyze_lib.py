from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, cast

from .common import (
    parse_transcript,
    TranscriptParse,
)
from .common.io import TranscriptSegment  # re-export for legacy imports
from .langgraph_orchestrator import build_analyze_graph, enable_langgraph_debug_logging
from .analyze.utils import FinalizedOutputs, AnalyzePipeline
from ..llm import LLMSettings, load_llm_settings
from ..llm.runtime import (
    ChatClient,
    ChatClientError,
    build_chat_client,
    build_provider_runtime_config,
)

BASE_DIR = Path(__file__).resolve().parents[3]
ANALYZE_DEFAULTS_PATH = BASE_DIR / "config" / "analyze_defaults.json"


@lru_cache(maxsize=1)
def load_analyze_defaults() -> Dict[str, Any]:
    try:
        payload = json.loads(ANALYZE_DEFAULTS_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def analyze_defaults() -> Dict[str, Any]:
    return dict(load_analyze_defaults())


_DEFAULTS = load_analyze_defaults()

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
    "analyze.extract_outline": int(_STAGE_LIMITS_DEFAULT.get("analyze.extract_outline", 12000)),
    "analyze.build_timeline_seeds": int(_STAGE_LIMITS_DEFAULT.get("analyze.build_timeline_seeds", 8000)),
    "analyze.build_entity_hints": int(_STAGE_LIMITS_DEFAULT.get("analyze.build_entity_hints", 8000)),
    "analyze.draft_markdown": int(_STAGE_LIMITS_DEFAULT.get("analyze.draft_markdown", 12000)),
    "analyze.qa_and_finalize": int(_STAGE_LIMITS_DEFAULT.get("analyze.qa_and_finalize", 6000)),
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

_STAGE_ALIAS_LOOKUP: Dict[str, str] = {}
for _attr, _stage_key in LLM_STAGE_KEYS.items():
    _STAGE_ALIAS_LOOKUP[_attr.lower()] = _stage_key
    _STAGE_ALIAS_LOOKUP[_stage_key.lower()] = _stage_key
    if _stage_key.startswith("analyze."):
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


logger = logging.getLogger("udocket.analyze.agent")

def _load_llm_settings() -> LLMSettings:
    global _llm_settings_cache
    if _llm_settings_cache is None:
        _llm_settings_cache = load_llm_settings()
    return _llm_settings_cache


@dataclass
class StageRuntime:
    stage_key: str
    providers: List[str]
    provider: str
    model: str
    client: Optional[ChatClient]
    max_output_tokens: int
    context_window_tokens: Optional[int]
    profile: StageProfile
    temperature: float
    options: Dict[str, Any] = field(default_factory=dict)

    @property
    def primary_provider(self) -> str:
        if self.providers:
            return self.providers[0]
        if self.provider:
            return self.provider
        return "azure"


def _credential_model_candidates(credential_payload: Optional[Dict[str, Any]]) -> List[str]:
    if not credential_payload:
        return []
    models_payload = credential_payload.get("models")
    if not isinstance(models_payload, (list, tuple)):
        return []
    enabled: List[str] = []
    disabled: List[str] = []
    for entry in models_payload:
        if not isinstance(entry, Mapping):
            continue
        name_value = entry.get("name") or entry.get("id")
        if not isinstance(name_value, str):
            continue
        name = name_value.strip()
        if not name:
            continue
        target = enabled if entry.get("enabled", True) else disabled
        if name not in target:
            target.append(name)
    return enabled + [value for value in disabled if value not in enabled]


def _provider_model_candidates(provider_meta: Optional["LLMProvider"]) -> List[str]:
    if provider_meta is None or not provider_meta.models:
        return []
    enabled: List[str] = []
    fallback: List[str] = []
    for name, model_meta in provider_meta.models.items():
        default_enabled = getattr(model_meta, "default_enabled", True)
        target = enabled if default_enabled else fallback
        if name not in target:
            target.append(name)
    return enabled + [value for value in fallback if value not in enabled]


def _model_candidates_for_provider(
    *,
    provider_meta: Optional["LLMProvider"],
    preferred_model: Optional[str],
    credential_payload: Optional[Dict[str, Any]],
) -> List[str]:
    candidates: List[str] = []

    def _add(value: Optional[str]) -> None:
        if not value or not isinstance(value, str):
            return
        normalized = value.strip()
        if not normalized:
            return
        if normalized not in candidates:
            candidates.append(normalized)

    _add(preferred_model)
    for name in _credential_model_candidates(credential_payload):
        _add(name)
    for name in _provider_model_candidates(provider_meta):
        _add(name)
    return candidates


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
    provider_chain: List[str] = field(
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
    provider_chain: List[str]


class AnalyzeAgent:
    def __init__(self, config: Optional[AnalyzeConfig] = None) -> None:
        self.config = config or AnalyzeConfig.from_env()
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

    def analyze(
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
        provider_credentials: Optional[Dict[str, Dict[str, Any]]] = None,
        progress_callback: Optional[
            Callable[[str, str, Dict[str, Any]], None]
        ] = None,
    ) -> AnalyzeResult:
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
            "analyze.start",
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
        if not provider_chain:
            provider_chain = list(DEFAULT_PROVIDER_CHAIN)

        provider_credentials = provider_credentials or {}

        stage_runtimes: Dict[str, StageRuntime] = {}
        provider_sequence: List[str] = []

        for stage_attr, stage_key in LLM_STAGE_KEYS.items():
            stage_profile = _stage_profile(stage_key)
            assignment = settings.stage(stage_key)
            providers = _normalize_providers(
                assignment.providers if assignment and assignment.providers else provider_chain
            )
            if not providers:
                providers = list(provider_chain or DEFAULT_PROVIDER_CHAIN)
            if not providers:
                providers = list(DEFAULT_PROVIDER_CHAIN)

            preferred_model = (
                str(assignment.model).strip()
                if assignment and assignment.model
                else ""
            )
            options: Dict[str, Any] = {}
            if assignment and assignment.options:
                options.update(dict(assignment.options))

            stage_config = stage_map.get(stage_key) or stage_map.get(stage_attr)
            override_max_tokens = None
            if stage_config:
                override_providers: Optional[List[str]] = None
                providers_payload = stage_config.get("providers")
                if isinstance(providers_payload, list):
                    override_providers = [str(value) for value in providers_payload]
                elif stage_config.get("provider"):
                    override_providers = [str(stage_config["provider"])]
                if override_providers is not None:
                    override_normalized = _normalize_providers(override_providers)
                    if override_normalized:
                        providers = override_normalized
                if stage_config.get("model"):
                    preferred_model = str(stage_config["model"]).strip()
                stage_options = stage_config.get("options")
                if isinstance(stage_options, dict):
                    for key, value in stage_options.items():
                        if key is None:
                            continue
                        options[str(key)] = value
                max_tokens_override = stage_config.get("max_tokens")
                if isinstance(max_tokens_override, (int, float, str)):
                    try:
                        override_max_tokens = max(1, int(float(str(max_tokens_override))))
                    except (TypeError, ValueError):
                        override_max_tokens = None

            if not providers:
                providers = _normalize_providers(self.config.provider_chain)
            if not providers:
                providers = list(DEFAULT_PROVIDER_CHAIN)
            if not providers:
                providers = ["azure"]

            requires_chat = stage_key != "analyze.context_builder"
            runtime: Optional[StageRuntime] = None
            errors: List[str] = []

            if requires_chat:
                for provider_name in providers:
                    provider_meta = settings.provider(provider_name)
                    if provider_meta is None:
                        errors.append(
                            f"{provider_name}: provider not configured"
                        )
                        continue
                    credential_payload = provider_credentials.get(provider_name)
                    model_candidates = _model_candidates_for_provider(
                        provider_meta=provider_meta,
                        preferred_model=preferred_model,
                        credential_payload=credential_payload,
                    )
                    if not model_candidates:
                        errors.append(
                            f"{provider_name}: no models available"
                        )
                        continue
                    for candidate_model in model_candidates:
                        resolved_options = dict(options)
                        try:
                            provider_runtime = build_provider_runtime_config(
                                provider=provider_meta,
                                model_name=candidate_model,
                                credential_payload=credential_payload,
                                options=resolved_options,
                            )
                            chat_client = build_chat_client(
                                provider_runtime=provider_runtime
                            )
                            candidate_meta = (
                                provider_runtime.model
                                if provider_runtime.model is not None
                                else provider_meta.models.get(candidate_model)
                            )
                            stage_max_tokens_base = (
                                candidate_meta.max_output_tokens
                                if candidate_meta and candidate_meta.max_output_tokens
                                else self.config.max_output_tokens
                            )
                            if override_max_tokens is not None:
                                stage_max_tokens_base = override_max_tokens
                            stage_max_tokens = self.config.stage_max_tokens_for(
                                stage_key,
                                candidate_meta.max_output_tokens if candidate_meta else None,
                                default_limit=stage_max_tokens_base,
                            )
                            stage_temperature = (
                                candidate_meta.default_temperature
                                if candidate_meta and candidate_meta.default_temperature is not None
                                else self.config.temperature
                            )
                            if "temperature" in resolved_options:
                                try:
                                    stage_temperature = float(resolved_options["temperature"])
                                except (TypeError, ValueError):
                                    pass

                            context_window_tokens = (
                                candidate_meta.context_window_tokens
                                if candidate_meta and candidate_meta.context_window_tokens
                                else None
                            )

                            runtime = StageRuntime(
                                stage_key=stage_key,
                                providers=providers,
                                provider=provider_name,
                                model=candidate_model,
                                client=chat_client,
                                max_output_tokens=stage_max_tokens or self.config.max_output_tokens,
                                context_window_tokens=context_window_tokens,
                                profile=stage_profile,
                                temperature=stage_temperature,
                                options=resolved_options,
                            )
                            break
                        except ChatClientError as exc:
                            errors.append(
                                f"{provider_name}:{candidate_model}: {exc}"
                            )
                        except Exception as exc:  # noqa: BLE001
                            errors.append(
                                f"{provider_name}:{candidate_model}: {exc}"
                            )
                    if runtime is not None:
                        break
            else:
                for provider_name in providers:
                    provider_meta = settings.provider(provider_name)
                    if provider_meta is None:
                        errors.append(
                            f"{provider_name}: provider not configured"
                        )
                        continue
                    credential_payload = provider_credentials.get(provider_name)
                    model_candidates = _model_candidates_for_provider(
                        provider_meta=provider_meta,
                        preferred_model=preferred_model,
                        credential_payload=credential_payload,
                    )
                    if not model_candidates:
                        errors.append(
                            f"{provider_name}: no models available"
                        )
                        continue
                    candidate_model = model_candidates[0]
                    candidate_meta = provider_meta.models.get(candidate_model)
                    stage_max_tokens_base = (
                        candidate_meta.max_output_tokens
                        if candidate_meta and candidate_meta.max_output_tokens
                        else self.config.max_output_tokens
                    )
                    if override_max_tokens is not None:
                        stage_max_tokens_base = override_max_tokens
                    stage_max_tokens = self.config.stage_max_tokens_for(
                        stage_key,
                        candidate_meta.max_output_tokens if candidate_meta else None,
                        default_limit=stage_max_tokens_base,
                    )
                    stage_temperature = (
                        candidate_meta.default_temperature
                        if candidate_meta and candidate_meta.default_temperature is not None
                        else self.config.temperature
                    )
                    if "temperature" in options:
                        try:
                            stage_temperature = float(options["temperature"])
                        except (TypeError, ValueError):
                            pass

                    context_window_tokens = (
                        candidate_meta.context_window_tokens
                        if candidate_meta and candidate_meta.context_window_tokens
                        else None
                    )

                    runtime = StageRuntime(
                        stage_key=stage_key,
                        providers=providers,
                        provider=provider_name,
                        model=candidate_model,
                        client=None,
                        max_output_tokens=stage_max_tokens or self.config.max_output_tokens,
                        context_window_tokens=context_window_tokens,
                        profile=stage_profile,
                        temperature=stage_temperature,
                        options=dict(options),
                    )
                    break

            if runtime is None:
                error_reason = ", ".join(errors) if errors else "no providers available"
                raise RuntimeError(
                    f"Unable to initialize providers for stage '{stage_key}': {error_reason}"
                )

            stage_runtimes[stage_key] = runtime

            for provider in runtime.providers:
                if provider not in provider_sequence:
                    provider_sequence.append(provider)

            self._log(
                self._log_level,
                "stage.configured",
                stage=stage_key,
                providers=runtime.providers,
                model=runtime.model,
                client_available=bool(runtime.client),
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
            transcript_path = self._resolve_transcript(
                state.get("input_path"), case_dir
            )

        pipeline.emit_pipeline_event(
            "complete",
            status=final_state.get("status", "ok"),
        )
        self._log(
            self._log_level,
            "analyze.completed",
            status=final_state.get("status", "ok"),
            summary=str(final_outputs.summary_path),
            outline=str(final_outputs.outline_path),
        )
        return AnalyzeResult(
            status=final_state.get("status", "ok"),
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
        self, pipeline: AnalyzePipeline, state: Dict[str, Any]
    ) -> Dict[str, Any]:
        current_state: Dict[str, Any] = dict(state)
        graph = None
        try:
            graph = build_analyze_graph(pipeline)
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
    "AnalyzeAgent",
    "AnalyzeConfig",
    "AnalyzeResult",
    "parse_transcript",
    "TranscriptParse",
    "TranscriptSegment",
    "DISALLOWED_PROVIDERS",
]
