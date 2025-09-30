from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, MutableMapping, Optional, cast

from ..common import (
    AnalysisArtifact,
    append_jsonl,
    ensure_dir,
    next_versioned,
    parse_transcript,
    sha256_file,
    TranscriptParse,
)
from .exceptions import AzureStageFailure, AzureUnavailableError
from .stages import (
    DraftStageResult,
    EntityStageResult,
    OutlineStageResult,
    TimelineStageResult,
    generate_entities,
    generate_outline,
    generate_summary_markdown,
    generate_timeline,
)

logger = logging.getLogger("udocket.summarize.pipeline")


REQUIRED_HEADINGS = {
    "Case metadata summary": "- Pending case metadata.",
    "Executive summary": "- Pending executive summary.",
    "Detailed narrative": "- Pending detailed narrative.",
    "Claims and remedies sought": "- Pending claims and remedies.",
    "Procedural posture, orders, and deadlines": "- Pending procedural posture details.",
    "Risks, gaps, and questions": "- Pending risk assessment.",
    "Next-step checklist": "- Pending next steps.",
}

DEFAULT_CHARS_PER_TOKEN = 4.0


@dataclass
class FinalizedOutputs:
    summary_path: Path
    outline_path: Path
    timeline_seed_path: Path
    entity_hint_path: Path
    case_brief_path: Path
    meta_path: Path
    audit_path: Path
    words: int
    sha_map: Dict[str, str]
    artifacts: Dict[str, AnalysisArtifact]
    offline_fallback_used: bool
    provider_chain: List[str]


class SummarizePipeline:
    """Single-run pipeline implementing the LangGraph node flow."""

    def __init__(
        self,
        *,
        case_id: str,
        job_id: str,
        case_dir: Path,
        intake: Optional[Dict[str, Any]],
        transcript_hint: Optional[Dict[str, Any]],
        config: Any,
        resolve_transcript: Callable[[Optional[Path], Path], Path],
        build_context: Callable[[TranscriptParse, Dict[str, Any]], str],
        provider_chain: Optional[List[str]],
        stage_runtimes: Dict[str, Any],
        default_temperature: float,
        global_allow_offline: bool,
        logger: Optional[logging.Logger] = None,
        progress_callback: Optional[
            Callable[[str, str, Dict[str, Any]], None]
        ] = None,
    ) -> None:
        self.case_id = case_id
        self.job_id = job_id
        self.case_dir = case_dir
        self.intake = intake or {}
        self.transcript_hint = transcript_hint
        self.config = config
        self._resolve_transcript: Callable[[Optional[Path], Path], Path] = (
            resolve_transcript
        )
        self._build_context: Callable[[TranscriptParse, Dict[str, Any]], str] = (
            build_context
        )
        self.stage_runtimes = stage_runtimes
        self.default_temperature = default_temperature
        self.global_allow_offline = global_allow_offline
        self.offline_fallback_used = False
        self.provider_chain = list(provider_chain or [])
        self.logger = logger or logging.getLogger("udocket.summarize.pipeline")
        self.progress_callback = progress_callback
        self.chars_per_token = (
            getattr(config, "chars_per_token", DEFAULT_CHARS_PER_TOKEN) or DEFAULT_CHARS_PER_TOKEN
        )
        self.prompt_chars_override = getattr(config, "prompt_chars_override", None)
        self.prompt_segments_override = getattr(config, "prompt_segments_override", None)
        self._log_level = (
            logging.INFO if getattr(config, "debug", False) else logging.DEBUG
        )
        self._log_enabled = (
            getattr(config, "debug", False)
            or self.logger.isEnabledFor(logging.DEBUG)
        )
        if not self.provider_chain:
            self.provider_chain = ["local"]
        # mark offline usage if any stage configured as local
        for runtime in stage_runtimes.values():
            if runtime.primary_provider == "local":
                self.offline_fallback_used = True
                break

    def emit_pipeline_event(self, event: str, **meta: Any) -> None:
        self._notify_stage("pipeline", event, **meta)

    # Internal logging helpers ----------------------------------------

    def _notify_stage(self, stage: str, event: str, **meta: Any) -> None:
        cleaned: Dict[str, Any] = {}
        for key, value in meta.items():
            if value is None:
                continue
            if isinstance(value, Path):
                cleaned[key] = str(value)
            else:
                cleaned[key] = value
        if self.progress_callback is None:
            self._log_stage(stage, event, cleaned)
        if self.progress_callback is not None:
            try:
                self.progress_callback(stage, event, dict(cleaned))
            except Exception:
                if self._log_enabled:
                    self.logger.exception(
                        "Progress callback failed",
                        extra={"stage": stage, "event": event},
                    )

    def _log_stage(self, stage: str, event: str, details: Dict[str, Any]) -> None:
        if not self._log_enabled:
            return
        suffix = " ".join(f"{key}={value}" for key, value in details.items())
        message = f"{stage}.{event}" if not suffix else f"{stage}.{event} | {suffix}"
        self.logger.log(self._log_level, message)

    # LangGraph-compatible node implementations -----------------------

    def input_discovery(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        input_path = state.get("input_path")
        self._notify_stage(
            "input_discovery",
            "start",
            input_hint=str(input_path) if input_path else None,
        )
        transcript_path = self._resolve_transcript(input_path, self.case_dir)
        state["transcript_path"] = transcript_path
        state["case_dir"] = self.case_dir
        self._notify_stage(
            "input_discovery",
            "complete",
            transcript=str(transcript_path),
        )
        return state

    def parse_transcript(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        self._notify_stage("parse_transcript", "start")
        transcript_path: Path = state["transcript_path"]
        parsed = parse_transcript(transcript_path)
        state["parse"] = parsed
        state.setdefault("token_usage", {})
        self._notify_stage(
            "parse_transcript",
            "complete",
            segments=len(parsed.segments),
            diarized=parsed.diarized,
        )
        return state

    def context_builder(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        self._notify_stage("context_builder", "start")
        parse: TranscriptParse = state["parse"]
        context_lines = self._collect_context_lines(parse)
        context_chunks: Dict[str, List[str]] = {}
        largest_snippet = ""
        for stage_key in self.stage_runtimes:
            chunks = self._build_context_chunks_for_stage(stage_key, context_lines)
            context_chunks[stage_key] = chunks
            if chunks:
                candidate = chunks[0]
                if len(candidate) > len(largest_snippet):
                    largest_snippet = candidate
        if not context_chunks:
            default_chunk = ["\n".join(context_lines)] if context_lines else [""]
            context_chunks["default"] = default_chunk
            largest_snippet = default_chunk[0]
        context_snippet = largest_snippet
        speakers = sorted({seg.speaker for seg in parse.segments if seg.speaker})
        timestamps = [seg.ts for seg in parse.segments if seg.ts is not None]
        duration = max(timestamps) if timestamps else None
        brief: Dict[str, Any] = {
            "case_id": self.case_id,
            "job_id": self.job_id,
            "header_lines": parse.header_lines,
            "intake": self.intake,
            "transcript": {
                "diarized": parse.diarized,
                "speakers": speakers,
                "approx_duration_seconds": duration,
                "segment_count": len(parse.segments),
            },
        }
        state["context_lines"] = context_lines
        state["context_chunks"] = context_chunks
        state["context_chunk_counts"] = {
            key: len(value) for key, value in context_chunks.items()
        }
        state["context_snippet"] = context_snippet
        state["case_brief"] = brief
        state.setdefault("offline_fallback_used", self.offline_fallback_used)
        state.setdefault("provider_chain", self.provider_chain)
        self._notify_stage(
            "context_builder",
            "complete",
            snippet_chars=len(context_snippet),
            speakers=len(speakers),
            duration_seconds=duration,
        )
        return state

    def extract_outline(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        parse: TranscriptParse = state["parse"]
        context_snippet = self._context_input_for_stage(
            "summarize.extract_outline", state
        )
        case_brief: Dict[str, Any] = state["case_brief"]
        runtime = self.stage_runtimes.get("summarize.extract_outline")
        azure_client = runtime.azure_client if runtime else None
        max_tokens = runtime.max_output_tokens if runtime and runtime.max_output_tokens else self.config.max_output_tokens
        temperature = runtime.temperature if runtime else self.default_temperature
        self._notify_stage(
            "extract_outline",
            "start",
            provider=runtime.primary_provider if runtime else None,
            azure_client=bool(azure_client),
        )
        try:
            outline_result = generate_outline(
                parse=parse,
                intake=self.intake,
                context_snippet=context_snippet,
                case_brief=case_brief,
                azure_client=azure_client,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except AzureStageFailure as exc:
            outline_result = self._handle_stage_failure(state, exc, runtime)
        state["outline_result"] = outline_result
        self._record_usage(state, "outline", outline_result.usage)
        if runtime:
            if runtime.primary_provider == "local":
                self.offline_fallback_used = True
                state["offline_fallback_used"] = True
            elif runtime.primary_provider == "azure" and runtime.allow_local_fallback and runtime.azure_client is None:
                self.offline_fallback_used = True
                state["offline_fallback_used"] = True
        outline_map: Dict[str, Any] = outline_result.outline
        issues_list = outline_map.get("issues")
        facts_list = outline_map.get("facts")
        issue_count = (
            len(cast(List[Any], issues_list))
            if isinstance(issues_list, list)
            else None
        )
        fact_count = (
            len(cast(List[Any], facts_list))
            if isinstance(facts_list, list)
            else None
        )
        self._notify_stage(
            "extract_outline",
            "complete",
            issues=issue_count,
            facts=fact_count,
            prompt_tokens=outline_result.usage.get("prompt_tokens"),
            completion_tokens=outline_result.usage.get("completion_tokens"),
        )
        return state

    def build_timeline_seeds(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        parse: TranscriptParse = state["parse"]
        context_snippet = self._context_input_for_stage(
            "summarize.build_timeline_seeds", state
        )
        outline_result: OutlineStageResult = state["outline_result"]
        case_brief: Dict[str, Any] = state["case_brief"]
        runtime = self.stage_runtimes.get("summarize.build_timeline_seeds")
        azure_client = runtime.azure_client if runtime else None
        max_tokens = runtime.max_output_tokens if runtime and runtime.max_output_tokens else self.config.max_output_tokens
        temperature = runtime.temperature if runtime else self.default_temperature
        self._notify_stage(
            "build_timeline_seeds",
            "start",
            provider=runtime.primary_provider if runtime else None,
            azure_client=bool(azure_client),
        )
        try:
            timeline_result = generate_timeline(
                parse=parse,
                outline_issues=outline_result.outline.get("issues", []),
                context_snippet=context_snippet,
                case_brief=case_brief,
                azure_client=azure_client,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except AzureStageFailure as exc:
            timeline_result = self._handle_stage_failure(state, exc, runtime)
        state["timeline_result"] = timeline_result
        self._record_usage(state, "timeline", timeline_result.usage)
        if runtime:
            if runtime.primary_provider == "local" or (runtime.primary_provider == "azure" and runtime.allow_local_fallback and runtime.azure_client is None):
                self.offline_fallback_used = True
                state["offline_fallback_used"] = True
        events_count = len(timeline_result.events)
        self._notify_stage(
            "build_timeline_seeds",
            "complete",
            events=events_count,
            prompt_tokens=timeline_result.usage.get("prompt_tokens"),
            completion_tokens=timeline_result.usage.get("completion_tokens"),
        )
        return state

    def build_entity_hints(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        parse: TranscriptParse = state["parse"]
        context_snippet = self._context_input_for_stage(
            "summarize.build_entity_hints", state
        )
        outline_result: OutlineStageResult = state["outline_result"]
        case_brief: Dict[str, Any] = state["case_brief"]
        runtime = self.stage_runtimes.get("summarize.build_entity_hints")
        azure_client = runtime.azure_client if runtime else None
        max_tokens = runtime.max_output_tokens if runtime and runtime.max_output_tokens else self.config.max_output_tokens
        temperature = runtime.temperature if runtime else self.default_temperature
        self._notify_stage(
            "build_entity_hints",
            "start",
            provider=runtime.primary_provider if runtime else None,
            azure_client=bool(azure_client),
        )
        try:
            entity_result = generate_entities(
                parse=parse,
                outline_parties=outline_result.outline.get("parties", {}),
                context_snippet=context_snippet,
                case_brief=case_brief,
                azure_client=azure_client,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except AzureStageFailure as exc:
            entity_result = self._handle_stage_failure(state, exc, runtime)
        state["entity_result"] = entity_result
        self._record_usage(state, "entities", entity_result.usage)
        if runtime:
            if runtime.primary_provider == "local" or (runtime.primary_provider == "azure" and runtime.allow_local_fallback and runtime.azure_client is None):
                self.offline_fallback_used = True
                state["offline_fallback_used"] = True
        entity_map: Dict[str, Any] = entity_result.hints
        entities_value = entity_map.get("entities")
        relations_value = entity_map.get("relations")
        entities_count = (
            len(cast(List[Any], entities_value))
            if isinstance(entities_value, list)
            else None
        )
        relations_count = (
            len(cast(List[Any], relations_value))
            if isinstance(relations_value, list)
            else None
        )
        self._notify_stage(
            "build_entity_hints",
            "complete",
            entities=entities_count,
            relations=relations_count,
            prompt_tokens=entity_result.usage.get("prompt_tokens"),
            completion_tokens=entity_result.usage.get("completion_tokens"),
        )
        return state

    def draft_markdown(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        parse: TranscriptParse = state["parse"]
        context_snippet = self._context_input_for_stage(
            "summarize.draft_markdown", state
        )
        outline_result: OutlineStageResult = state["outline_result"]
        timeline_result: TimelineStageResult = state["timeline_result"]
        entity_result: EntityStageResult = state["entity_result"]
        case_brief: Dict[str, Any] = state["case_brief"]
        runtime = self.stage_runtimes.get("summarize.draft_markdown")
        azure_client = runtime.azure_client if runtime else None
        max_tokens = runtime.max_output_tokens if runtime and runtime.max_output_tokens else self.config.max_output_tokens
        temperature = runtime.temperature if runtime else self.default_temperature
        self._notify_stage(
            "draft_markdown",
            "start",
            provider=runtime.primary_provider if runtime else None,
            azure_client=bool(azure_client),
        )
        try:
            summary_result = generate_summary_markdown(
                parse=parse,
                outline=outline_result.outline,
                timeline=timeline_result.events,
                entities=entity_result.hints,
                intake=self.intake,
                context_snippet=context_snippet,
                case_brief=case_brief,
                azure_client=azure_client,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except AzureStageFailure as exc:
            summary_result = self._handle_stage_failure(state, exc, runtime)
        state["summary_result"] = summary_result
        self._record_usage(state, "summary", summary_result.usage)
        if runtime:
            if runtime.primary_provider == "local" or (runtime.primary_provider == "azure" and runtime.allow_local_fallback and runtime.azure_client is None):
                self.offline_fallback_used = True
                state["offline_fallback_used"] = True
        words = len(summary_result.markdown.split()) if summary_result.markdown else 0
        self._notify_stage(
            "draft_markdown",
            "complete",
            words=words,
            prompt_tokens=summary_result.usage.get("prompt_tokens"),
            completion_tokens=summary_result.usage.get("completion_tokens"),
        )
        return state

    def qa_and_finalize(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        self._notify_stage("qa_and_finalize", "start")
        parse: TranscriptParse = state["parse"]
        runtime = self.stage_runtimes.get("summarize.qa_and_finalize")
        if runtime and runtime.primary_provider == "local":
            self.offline_fallback_used = True
        summary_result: DraftStageResult = state["summary_result"]
        markdown = summary_result.markdown.strip()
        markdown = self._ensure_header(markdown, parse)
        markdown = self._ensure_sections(markdown)
        state["summary_result"] = DraftStageResult(markdown=markdown, usage=summary_result.usage)
        self._notify_stage(
            "qa_and_finalize",
            "complete",
            length=len(markdown),
        )
        return state

    def write_ops_and_artifacts(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        self._notify_stage("write_ops_and_artifacts", "start")
        parse: TranscriptParse = state["parse"]
        outline_result: OutlineStageResult = state["outline_result"]
        timeline_result: TimelineStageResult = state["timeline_result"]
        entity_result: EntityStageResult = state["entity_result"]
        summary_result: DraftStageResult = state["summary_result"]
        transcript_path: Path = state["transcript_path"]
        token_usage: Dict[str, Dict[str, int]] = state.get("token_usage", {})
        case_brief: Dict[str, Any] = state.get("case_brief", {})
        offline_flag = state.get("offline_fallback_used", self.offline_fallback_used)

        finalized = finalize_outputs(
            case_id=self.case_id,
            job_id=self.job_id,
            case_dir=self.case_dir,
            transcript_path=transcript_path,
            parse_diarized=parse.diarized,
            outline_result=outline_result,
            timeline_result=timeline_result,
            entity_result=entity_result,
            summary_result=summary_result,
            intake_payload=self.intake,
            config=self.config,
            token_usage=token_usage,
            case_brief=case_brief,
            offline_fallback_used=offline_flag,
            provider_chain=self.provider_chain,
            transcript_hint=self.transcript_hint,
        )
        state["final_outputs"] = finalized
        state["status"] = "ok"
        self._notify_stage(
            "write_ops_and_artifacts",
            "complete",
            summary=str(finalized.summary_path),
            outline=str(finalized.outline_path),
            timeline=str(finalized.timeline_seed_path),
            entities=str(finalized.entity_hint_path),
            offline=offline_flag,
        )
        return state

    # Internal helpers -------------------------------------------------

    def _context_input_for_stage(
        self, stage_key: str, state: MutableMapping[str, Any]
    ) -> Any:
        context_chunks: Dict[str, List[str]] = state.get("context_chunks", {})
        chunks = context_chunks.get(stage_key)
        if not chunks:
            return state.get("context_snippet", "")
        if len(chunks) == 1:
            return chunks[0]
        if stage_key in {"summarize.draft_markdown", "summarize.qa_and_finalize"}:
            return chunks[0]
        return chunks

    def _collect_context_lines(self, parse: TranscriptParse) -> List[str]:
        lines: List[str] = []
        case_number = self.intake.get("court_case_number")
        if case_number:
            lines.append(f"Case number: {case_number}")
        for header in parse.header_lines:
            header_clean = header.strip()
            if header_clean:
                lines.append(header_clean)
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
            elif seg.speaker:
                prefix = f"{seg.speaker}: "
            lines.append(prefix + text)
        return lines

    def _build_context_chunks_for_stage(
        self, stage_key: str, lines: List[str]
    ) -> List[str]:
        if not lines:
            return [""]
        segment_limit = self._segment_limit()
        usable_lines = lines[:segment_limit] if segment_limit is not None else list(lines)
        if not usable_lines:
            usable_lines = lines
        char_limit = self._char_limit_for_stage(stage_key)
        if not char_limit or char_limit <= 0:
            return ["\n".join(usable_lines)]
        chunks: List[str] = []
        current: List[str] = []
        current_chars = 0
        for line in usable_lines:
            line_len = len(line) + 1
            if current and current_chars + line_len > char_limit:
                chunks.append("\n".join(current))
                current = []
                current_chars = 0
            current.append(line)
            current_chars += line_len
        if current:
            chunks.append("\n".join(current))
        return chunks or ["\n".join(usable_lines)]

    def _segment_limit(self) -> Optional[int]:
        override = self.prompt_segments_override
        if override is None or override <= 0:
            return None
        return override

    def _char_limit_for_stage(self, stage_key: str) -> Optional[int]:
        runtime = self.stage_runtimes.get(stage_key)
        manual_limit = self.prompt_chars_override
        if runtime is None:
            if manual_limit is not None and manual_limit > 0:
                return manual_limit
            return None
        context_tokens = runtime.context_window_tokens
        if context_tokens is not None:
            available = context_tokens - runtime.profile.output_reserve_tokens
            context_tokens = max(available, runtime.profile.min_context_tokens)
        else:
            context_tokens = runtime.profile.recommended_context_tokens
        chunk_target = runtime.profile.target_chunk_tokens
        if chunk_target:
            context_tokens = min(context_tokens, chunk_target)
        char_limit = (
            int(context_tokens * self.chars_per_token)
            if context_tokens
            else None
        )
        if manual_limit is not None and manual_limit > 0:
            char_limit = min(char_limit or manual_limit, manual_limit)
        return char_limit

    def _record_usage(self, state: MutableMapping[str, Any], stage: str, usage: Dict[str, int]) -> None:
        if not usage:
            return
        token_usage: Dict[str, Dict[str, int]] = state.setdefault("token_usage", {})
        token_usage[stage] = usage

    def _handle_stage_failure(
        self,
        state: MutableMapping[str, Any],
        exc: AzureStageFailure,
        runtime: Optional[Any],
    ) -> Any:
        allow = False
        if runtime and runtime.primary_provider == "local":
            allow = True
        elif runtime and runtime.allow_local_fallback and self.global_allow_offline:
            allow = True
        if self._log_enabled:
            self.logger.warning(
                "stage failure",
                extra={
                    "stage": exc.stage,
                    "error": str(exc.error),
                    "job_id": getattr(self, "job_id", None),
                    "case_id": getattr(self, "case_id", None),
                },
            )
        self._notify_stage(
            exc.stage,
            "failure",
            error=str(exc.error),
            fallback_allowed=allow,
        )
        if allow:
            state["offline_fallback_used"] = True
            self.offline_fallback_used = True
            self._notify_stage(exc.stage, "fallback", provider="local")
            return exc.fallback
        raise AzureUnavailableError(exc.stage, exc.error) from exc

    def _ensure_header(self, markdown: str, parse: TranscriptParse) -> str:
        stripped = markdown.lstrip()
        if stripped.startswith("# "):
            return markdown
        header_lines = [line.strip() for line in parse.header_lines if line.strip()]
        if header_lines:
            heading = header_lines[0]
            remainder = "\n".join(header_lines[1:])
            header_block = f"# {heading}\n"
            if remainder:
                header_block += f"{remainder}\n"
        else:
            header_block = f"# Summary for case {self.case_id} (job {self.job_id})\n"
        return header_block + "\n" + stripped

    def _ensure_sections(self, markdown: str) -> str:
        updated = markdown.rstrip()
        for heading, placeholder in REQUIRED_HEADINGS.items():
            if not self._has_heading(updated, heading):
                updated += f"\n\n## {heading}\n{placeholder}"
        return updated + "\n"

    @staticmethod
    def _has_heading(markdown: str, heading: str) -> bool:
        pattern = rf"^##\s+{re.escape(heading)}\s*$"
        return re.search(pattern, markdown, re.IGNORECASE | re.MULTILINE) is not None


def finalize_outputs(
    *,
    case_id: str,
    job_id: str,
    case_dir: Path,
    transcript_path: Path,
    parse_diarized: bool,
    outline_result: OutlineStageResult,
    timeline_result: TimelineStageResult,
    entity_result: EntityStageResult,
    summary_result: DraftStageResult,
    intake_payload: Dict[str, Any],
    config: Any,
    token_usage: Dict[str, Dict[str, int]],
    case_brief: Dict[str, Any],
    offline_fallback_used: bool,
    provider_chain: Optional[list[str]],
    transcript_hint: Optional[Dict[str, Any]] = None,
) -> FinalizedOutputs:
    analysis_dir = case_dir / "analysis"
    ops_dir = case_dir / "ops"
    ensure_dir(analysis_dir)
    ensure_dir(ops_dir)

    summary_path = next_versioned(analysis_dir / f"{job_id}__summary_v1.md")
    summary_path.write_text(summary_result.markdown, encoding="utf-8")

    outline_path = next_versioned(analysis_dir / f"{job_id}__outline_v1.json")
    outline_path.write_text(json.dumps(outline_result.outline, ensure_ascii=False, indent=2), encoding="utf-8")

    timeline_path = next_versioned(analysis_dir / f"{job_id}__timeline_seeds_v1.json")
    timeline_payload = {"events": timeline_result.events}
    timeline_path.write_text(json.dumps(timeline_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    entity_path = next_versioned(analysis_dir / f"{job_id}__entity_hints_v1.json")
    entity_path.write_text(json.dumps(entity_result.hints, ensure_ascii=False, indent=2), encoding="utf-8")

    case_brief_payload = case_brief or {}
    case_brief_path = next_versioned(analysis_dir / f"{job_id}__case_brief_v1.json")
    case_brief_path.write_text(
        json.dumps(case_brief_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary_sha = sha256_file(summary_path)
    outline_sha = sha256_file(outline_path)
    timeline_sha = sha256_file(timeline_path)
    entity_sha = sha256_file(entity_path)
    case_brief_sha = sha256_file(case_brief_path)

    sha_map = {
        "summary": summary_sha,
        "outline": outline_sha,
        "timeline": timeline_sha,
        "entities": entity_sha,
        "case_brief": case_brief_sha,
    }

    words = len(summary_result.markdown.split())

    timestamp_utc = (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )

    meta: Dict[str, Any] = {
        "case_id": case_id,
        "job_id": job_id,
        "source_transcript": str(transcript_path),
        "summary_file": summary_path.name,
        "summary_sha256": summary_sha,
        "outline_file": outline_path.name,
        "outline_sha256": outline_sha,
        "timeline_seeds_file": timeline_path.name,
        "timeline_seeds_sha256": timeline_sha,
        "entity_hints_file": entity_path.name,
        "entity_hints_sha256": entity_sha,
        "case_brief_file": case_brief_path.name,
        "case_brief_sha256": case_brief_sha,
        "language": getattr(config, "language", "en-CA"),
        "azure_enabled": getattr(config, "azure_enabled", False),
        "azure_region": getattr(config, "azure_region", None),
        "timestamp_utc": timestamp_utc,
        "status": "ok",
        "words": words,
        "diarized": parse_diarized,
        "facts": len(outline_result.outline.get("facts", [])),
        "timeline_events": len(timeline_result.events),
        "entity_count": len(entity_result.hints.get("entities", [])),
        "offline_fallback_used": offline_fallback_used,
    }
    if provider_chain:
        meta["provider_chain"] = list(provider_chain)
    if intake_payload:
        meta["intake"] = intake_payload
    if transcript_hint:
        meta["transcript_hint"] = transcript_hint
    if token_usage:
        meta["token_usage"] = token_usage

    meta_path = ops_dir / f"{job_id}__summary_log.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    audit_path = ops_dir / "ops_summary.jsonl"
    append_jsonl(
        audit_path,
        {
            "ts": meta["timestamp_utc"],
            "case_id": case_id,
            "job_id": job_id,
            "event": "summary.created",
            "summary_file": str(summary_path),
            "outline_file": str(outline_path),
            "timeline_file": str(timeline_path),
            "entity_file": str(entity_path),
            "case_brief_file": str(case_brief_path),
            "words": words,
            "providers": provider_chain or [],
        },
    )

    artifacts = {
        "summary": AnalysisArtifact("summary", summary_path, summary_sha, {}),
        "outline": AnalysisArtifact("outline", outline_path, outline_sha, {}),
        "timeline": AnalysisArtifact("timeline", timeline_path, timeline_sha, {}),
        "entities": AnalysisArtifact("entities", entity_path, entity_sha, {}),
        "case_brief": AnalysisArtifact("case_brief", case_brief_path, case_brief_sha, {}),
    }

    return FinalizedOutputs(
        summary_path=summary_path,
        outline_path=outline_path,
        timeline_seed_path=timeline_path,
        entity_hint_path=entity_path,
        case_brief_path=case_brief_path,
        meta_path=meta_path,
        audit_path=audit_path,
        words=words,
        sha_map=sha_map,
        artifacts=artifacts,
        offline_fallback_used=offline_fallback_used,
        provider_chain=list(provider_chain or []),
    )


__all__ = ["FinalizedOutputs", "SummarizePipeline", "finalize_outputs"]
