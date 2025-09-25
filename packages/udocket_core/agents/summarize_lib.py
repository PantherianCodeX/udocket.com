from __future__ import annotations

import os
from dataclasses import dataclass
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

MAX_PROMPT_SEGMENTS = 120
MAX_PROMPT_CHARS = 8000


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

    @classmethod
    def from_env(cls) -> "SummarizeConfig":
        endpoint = (os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip()
        key = (os.getenv("AZURE_OPENAI_API_KEY") or "").strip()
        deployment = (os.getenv("AZURE_OPENAI_DEPLOYMENT") or "").strip()
        api_version = (os.getenv("AZURE_OPENAI_API_VERSION") or "2024-08-01-preview").strip()
        language = (os.getenv("LANGUAGE") or "en-CA").strip() or "en-CA"
        temperature = float(os.getenv("SUMMARY_TEMPERATURE", "0.2") or 0.2)
        max_tokens = int(os.getenv("SUMMARY_MAX_TOKENS", "24000") or 24000)
        debug = (os.getenv("DEBUG", "0").strip() == "1")
        allow_offline = (os.getenv("SUMMARY_ALLOW_OFFLINE_FALLBACK", "0").strip() == "1")
        force_offline = (os.getenv("SUMMARY_FORCE_OFFLINE", "0").strip() == "1")

        if endpoint and not _endpoint_is_canadian(endpoint):
            raise ValueError("AZURE_OPENAI_ENDPOINT must target canadacentral or canadaeast")

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
        )

    @property
    def azure_enabled(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_key and self.azure_openai_deployment)

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
    ) -> SummarizeResult:
        case_dir = Path(case_dir)
        state: Dict[str, Any] = {
            "case_id": case_id,
            "job_id": job_id,
            "case_dir": case_dir,
        }
        if input is not None:
            state["input_path"] = Path(input)

        azure_client = None
        azure_cfg = self.config.azure_client_config()
        if not self.config.force_offline_mode and azure_cfg is not None:
            azure_client = AzureChatClient(azure_cfg)

        offline_flag = (
            allow_offline_fallback
            if allow_offline_fallback is not None
            else self.config.enable_offline_fallback
        )
        pipeline = SummarizePipeline(
            case_id=case_id,
            job_id=job_id,
            case_dir=case_dir,
            intake=intake,
            transcript_hint=transcript_hint,
            config=self.config,
            azure_client=azure_client,
            resolve_transcript=self._resolve_transcript,
            build_context=self._build_context,
            allow_offline_fallback=offline_flag,
        )

        final_state = self._execute_pipeline(pipeline, state)
        final_outputs = final_state.get("final_outputs")
        if not isinstance(final_outputs, FinalizedOutputs):
            raise RuntimeError("Summarize pipeline did not produce outputs")

        transcript_path = final_state.get("transcript_path")
        if not isinstance(transcript_path, Path):
            transcript_path = self._resolve_transcript(state.get("input_path"), case_dir)

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
        )

    def _execute_pipeline(self, pipeline: SummarizePipeline, state: Dict[str, Any]) -> Dict[str, Any]:
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

    def _resolve_transcript(self, input_path: Optional[Path], case_dir: Path) -> Path:
        if input_path:
            resolved = Path(input_path)
            if not resolved.exists():
                raise FileNotFoundError(f"Transcript not found at {resolved}")
            return resolved
        transcript_dir = case_dir / "transcript"
        if not transcript_dir.exists():
            raise FileNotFoundError(f"No transcript directory at {transcript_dir}")
        candidates = sorted(
            (p for p in transcript_dir.glob("*__transcript.txt") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            raise FileNotFoundError("No transcript files found for case")
        return candidates[0]

    def _build_context(self, parse: TranscriptParse, intake: Dict[str, Any]) -> str:
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
            if len(snippets) >= MAX_PROMPT_SEGMENTS or chars >= MAX_PROMPT_CHARS:
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
