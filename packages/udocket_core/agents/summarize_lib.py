from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .common import (
    AzureChatClient,
    AzureClientConfig,
    parse_transcript,
    TranscriptParse,
)
from .common.azure_client import _endpoint_is_canadian
from .common.io import TranscriptSegment  # re-export for legacy imports
from .langgraph_orchestrator import build_summarize_graph
from .summarize.utils import FinalizedOutputs, SummarizePipeline
from ..llm import LLMSettings, load_llm_settings

MAX_PROMPT_SEGMENTS = 120
MAX_PROMPT_CHARS = 8000

SUPPORTED_PROVIDERS = {"azure", "local"}
DEFAULT_PROVIDER_CHAIN: List[str] = ["azure", "local"]
LLM_STAGE_KEYS = {
    "context_builder": "summarize.context_builder",
    "extract_outline": "summarize.extract_outline",
    "build_timeline_seeds": "summarize.build_timeline_seeds",
    "build_entity_hints": "summarize.build_entity_hints",
    "draft_markdown": "summarize.draft_markdown",
    "qa_and_finalize": "summarize.qa_and_finalize",
}
LLM_SETTINGS: Optional[LLMSettings] = None


def _load_llm_settings() -> LLMSettings:
    global LLM_SETTINGS
    if LLM_SETTINGS is None:
        LLM_SETTINGS = load_llm_settings()
    return LLM_SETTINGS


@dataclass
class StageRuntime:
    stage_key: str
    providers: List[str]
    model: str
    azure_client: Optional[AzureChatClient]
    max_output_tokens: int
    allow_local_fallback: bool
    temperature: float

    @property
    def primary_provider(self) -> str:
        return self.providers[0] if self.providers else "local"


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
    azure_openai_api_version: str = "2024-08-01-preview"
    language: str = "en-CA"
    temperature: float = 0.2
    max_output_tokens: int = 24000
    debug: bool = False
    enable_offline_fallback: bool = False
    force_offline_mode: bool = False
    provider_chain: List[str] = field(
        default_factory=lambda: list(DEFAULT_PROVIDER_CHAIN)
    )

    @classmethod
    def from_env(cls) -> "SummarizeConfig":
        endpoint = (os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip()
        key = (os.getenv("AZURE_OPENAI_API_KEY") or "").strip()
        deployment = (os.getenv("AZURE_OPENAI_DEPLOYMENT") or "").strip()
        api_version = (
            os.getenv("AZURE_OPENAI_API_VERSION") or "2024-08-01-preview"
        ).strip()
        language = (os.getenv("LANGUAGE") or "en-CA").strip() or "en-CA"
        temperature = float(os.getenv("SUMMARY_TEMPERATURE", "0.2") or 0.2)
        max_tokens = int(os.getenv("SUMMARY_MAX_TOKENS", "24000") or 24000)
        debug = os.getenv("DEBUG", "0").strip() == "1"
        allow_offline = (
            os.getenv("SUMMARY_ALLOW_OFFLINE_FALLBACK", "0").strip() == "1"
        )
        force_offline = os.getenv("SUMMARY_FORCE_OFFLINE", "0").strip() == "1"
        primary_provider = (
            (os.getenv("SUMMARY_PRIMARY_PROVIDER") or "azure").strip().lower()
        )
        fallback_raw = os.getenv("SUMMARY_FALLBACK_PROVIDERS")
        fallback_values: List[str] = []
        if fallback_raw is None:
            if primary_provider == "azure":
                fallback_values = ["local"]
        else:
            fallback_values = [
                value.strip().lower()
                for value in fallback_raw.split(",")
                if value.strip()
            ]

        providers = [primary_provider] + fallback_values
        filtered_chain: List[str] = []
        for provider in providers:
            if not provider:
                continue
            if provider not in SUPPORTED_PROVIDERS:
                raise ValueError(
                    "Unsupported summarize provider " f"'{provider}'"
                )
            if provider in filtered_chain:
                continue
            filtered_chain.append(provider)
        if not filtered_chain:
            filtered_chain = list(DEFAULT_PROVIDER_CHAIN)
        if force_offline:
            filtered_chain = ["local"]

        if endpoint and not _endpoint_is_canadian(endpoint):
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT must target canadacentral or canadaeast"
            )

        return cls(
            azure_openai_endpoint=endpoint,
            azure_openai_key=key,
            azure_openai_deployment=deployment,
            azure_openai_api_version=api_version,
            language=language,
            temperature=temperature,
            max_output_tokens=max_tokens,
            debug=debug,
            enable_offline_fallback=allow_offline,
            force_offline_mode=force_offline,
            provider_chain=filtered_chain,
        )

    @property
    def azure_enabled(self) -> bool:
        if self.force_offline_mode:
            return False
        if "azure" not in self.provider_chain:
            return False
        return bool(
            self.azure_openai_endpoint
            and self.azure_openai_key
            and self.azure_openai_deployment
        )

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
        return AzureClientConfig(
            endpoint=self.azure_openai_endpoint,
            key=self.azure_openai_key,
            deployment=self.azure_openai_deployment,
            api_version=self.azure_openai_api_version,
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
    offline_fallback_used: bool


class SummarizeAgent:
    def __init__(self, config: Optional[SummarizeConfig] = None) -> None:
        self.config = config or SummarizeConfig.from_env()

    def summarize(
        self,
        *,
        input: Optional[Path] = None,
        case_id: str,
        case_dir: Path,
        job_id: str,
        intake: Optional[Dict[str, Any]] = None,
        transcript_hint: Optional[Dict[str, Any]] = None,
        allow_offline_fallback: Optional[bool] = None,
        provider_chain: Optional[List[str]] = None,
        stage_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> SummarizeResult:
        case_dir = Path(case_dir)
        state: Dict[str, Any] = {
            "case_id": case_id,
            "job_id": job_id,
            "case_dir": case_dir,
        }
        if input is not None:
            state["input_path"] = Path(input)

        settings = _load_llm_settings()
        stage_overrides = stage_overrides or {}

        if allow_offline_fallback is None:
            global_allow_offline = self.config.enable_offline_fallback
        else:
            global_allow_offline = bool(allow_offline_fallback)

        if provider_chain is None:
            provider_chain = list(self.config.provider_chain)
        else:
            provider_chain = [
                value
                for value in provider_chain
                if value in SUPPORTED_PROVIDERS
            ]
        if not provider_chain:
            provider_chain = list(DEFAULT_PROVIDER_CHAIN)
        if self.config.force_offline_mode:
            provider_chain = ["local"]

        azure_enabled = self.config.azure_enabled
        stage_runtimes: Dict[str, StageRuntime] = {}
        provider_sequence: List[str] = []

        for stage_attr, stage_key in LLM_STAGE_KEYS.items():
            assignment = settings.stage(stage_key)
            providers = list(
                assignment.providers
                if assignment and assignment.providers
                else provider_chain
            )
            model = (
                assignment.model
                if assignment and assignment.model
                else (providers[0] if providers else "local")
            )
            options = dict(assignment.options) if assignment else {}

            override = stage_overrides.get(stage_key) or stage_overrides.get(
                stage_attr
            )
            if override:
                override_providers = override.get("providers")
                if isinstance(override_providers, list) and override_providers:
                    providers = [
                        p
                        for p in override_providers
                        if p in SUPPORTED_PROVIDERS
                    ]
                else:
                    primary_override = override.get("provider")
                    fallbacks_override = (
                        override.get("fallbacks")
                        if isinstance(override.get("fallbacks"), list)
                        else []
                    )
                    chain_override: List[str] = []
                    if primary_override:
                        chain_override.append(primary_override)
                    chain_override.extend(fallbacks_override)
                    if chain_override:
                        providers = [
                            p
                            for p in chain_override
                            if p in SUPPORTED_PROVIDERS
                        ]
                if override.get("model"):
                    model = str(override["model"])
                if isinstance(override.get("options"), dict):
                    options.update(
                        {
                            str(key): str(value)
                            for key, value in override["options"].items()
                        }
                    )

            providers = [p for p in providers if p in SUPPORTED_PROVIDERS]
            if not providers:
                providers = list(DEFAULT_PROVIDER_CHAIN)
            if self.config.force_offline_mode:
                providers = ["local"]

            model = model or providers[0]

            provider_meta = settings.provider(providers[0])
            model_meta = (
                provider_meta.models.get(model)
                if provider_meta and model in provider_meta.models
                else None
            )

            deployment = options.get("azure_deployment") if options else None
            if not deployment and model_meta and model_meta.deployment_env:
                deployment = os.getenv(model_meta.deployment_env)

            azure_client: Optional[AzureChatClient] = None
            if providers[0] == "azure" and azure_enabled:
                cfg = self.config.azure_client_config_for(deployment)
                if cfg:
                    azure_client = AzureChatClient(cfg)

            stage_max_tokens = (
                model_meta.max_output_tokens
                if model_meta and model_meta.max_output_tokens
                else self.config.max_output_tokens
            )
            stage_temperature = (
                model_meta.default_temperature
                if model_meta and model_meta.default_temperature is not None
                else self.config.temperature
            )

            allow_override = (
                override.get("allow_offline_fallback") if override else None
            )
            allow_local = providers[0] == "local" or ("local" in providers[1:])
            if allow_override is not None:
                allow_local = bool(allow_override)
            if not global_allow_offline and providers[0] != "local":
                allow_local = False

            runtime = StageRuntime(
                stage_key=stage_key,
                providers=providers,
                model=model,
                azure_client=azure_client,
                max_output_tokens=stage_max_tokens
                or self.config.max_output_tokens,
                allow_local_fallback=allow_local,
                temperature=stage_temperature,
            )
            stage_runtimes[stage_key] = runtime

            for provider in providers:
                if provider not in provider_sequence:
                    provider_sequence.append(provider)

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
            global_allow_offline=global_allow_offline,
        )

        final_state = self._execute_pipeline(pipeline, state)
        final_outputs = final_state.get("final_outputs")
        if not isinstance(final_outputs, FinalizedOutputs):
            raise RuntimeError("Summarize pipeline did not produce outputs")

        transcript_path = final_state.get("transcript_path")
        if not isinstance(transcript_path, Path):
            transcript_path = self._resolve_transcript(
                state.get("input_path"), case_dir
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
            offline_fallback_used=final_outputs.offline_fallback_used,
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
            return graph.invoke(current_state)
        for node_name in PIPELINE_NODE_ORDER:
            node = getattr(pipeline, node_name)
            current_state = node(current_state)
        return current_state

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
                len(snippets) >= MAX_PROMPT_SEGMENTS
                or chars >= MAX_PROMPT_CHARS
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
]
