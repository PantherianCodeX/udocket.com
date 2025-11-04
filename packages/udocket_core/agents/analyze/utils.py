from __future__ import annotations

import logging
import re
from collections.abc import Callable, MutableMapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from packages.udocket_common.json_utils import coerce_json_object, write_json_object
from packages.udocket_core import __version__ as UDOCKET_CORE_VERSION

from ..common import (
    AnalysisArtifact,
    TranscriptParse,
    append_jsonl,
    coerce_mapping,
    coerce_mapping_list,
    coerce_sequence,
    ensure_dir,
    next_versioned,
    parse_transcript,
    sequence_length,
    sha256_file,
)
from .stages import (
    EntityStageResult,
    OutlineStageResult,
    SummaryStageResult,
    TimelineStageResult,
    generate_entities,
    generate_outline,
    generate_summary_payload,
    generate_timeline,
)

if TYPE_CHECKING:  # pragma: no cover - circular import guard
    from ..analyze_lib import StageRuntime

logger = logging.getLogger("udocket.analyze.pipeline")


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
    summary_path: Path  # structured JSON
    summary_markdown_path: Path
    outline_path: Path
    timeline_seed_path: Path
    entity_hint_path: Path
    case_brief_path: Path
    meta_path: Path
    audit_path: Path
    words: int
    sha_map: dict[str, str]
    artifacts: dict[str, AnalysisArtifact]
    provider_chain: list[str]


class AnalyzePipeline:
    """Single-run pipeline implementing the LangGraph node flow."""

    def __init__(
        self,
        *,
        case_id: str,
        job_id: str,
        case_dir: Path,
        intake: dict[str, Any] | None,
        transcript_hint: dict[str, Any] | None,
        config: Any,
        resolve_transcript: Callable[[Path | None, Path], Path],
        build_context: Callable[[TranscriptParse, dict[str, Any]], str],
        provider_chain: list[str] | None,
        stage_runtimes: dict[str, StageRuntime],
        default_temperature: float,
        logger: logging.Logger | None = None,
        progress_callback: Callable[[str, str, dict[str, Any]], None] | None = None,
    ) -> None:
        self.case_id = case_id
        self.job_id = job_id
        self.case_dir = case_dir
        self.intake = intake or {}
        self.transcript_hint = transcript_hint
        self.config = config
        self._resolve_transcript: Callable[[Path | None, Path], Path] = resolve_transcript
        self._build_context: Callable[[TranscriptParse, dict[str, Any]], str] = build_context
        self.stage_runtimes = stage_runtimes
        self.default_temperature = default_temperature
        self.provider_chain = list(provider_chain or [])
        self.logger = logger or logging.getLogger("udocket.analyze.pipeline")
        self.progress_callback = progress_callback
        self.chars_per_token = (
            getattr(config, "chars_per_token", DEFAULT_CHARS_PER_TOKEN) or DEFAULT_CHARS_PER_TOKEN
        )
        self.prompt_chars_override = getattr(config, "prompt_chars_override", None)
        self.prompt_segments_override = getattr(config, "prompt_segments_override", None)
        self._log_level = logging.INFO if getattr(config, "debug", False) else logging.DEBUG
        self._log_enabled = getattr(config, "debug", False) or self.logger.isEnabledFor(
            logging.DEBUG
        )
        if not self.provider_chain:
            self.provider_chain = ["azure"]

    def emit_pipeline_event(self, event: str, **meta: Any) -> None:
        self._notify_stage("pipeline", event, **meta)

    # Internal logging helpers ----------------------------------------

    def _notify_stage(self, stage: str, event: str, **meta: Any) -> None:
        cleaned: dict[str, Any] = {}
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

    def _log_stage(self, stage: str, event: str, details: dict[str, Any]) -> None:
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
        context_chunks: dict[str, list[str]] = {}
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
        brief: dict[str, Any] = {
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
        state["context_chunk_counts"] = {key: len(value) for key, value in context_chunks.items()}
        state["context_snippet"] = context_snippet
        state["case_brief"] = brief
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
        context_snippet = self._context_input_for_stage("analyze.extract_outline", state)
        case_brief: dict[str, Any] = state["case_brief"]
        runtime = self.stage_runtimes.get("analyze.extract_outline")
        llm_client = runtime.client if runtime else None
        max_tokens = (
            runtime.max_output_tokens
            if runtime and runtime.max_output_tokens
            else self.config.max_output_tokens
        )
        temperature = runtime.temperature if runtime else self.default_temperature
        self._notify_stage(
            "extract_outline",
            "start",
            provider=runtime.primary_provider if runtime else None,
            client_available=bool(llm_client),
        )
        try:
            outline_result = generate_outline(
                parse=parse,
                intake=self.intake,
                context_snippet=context_snippet,
                case_brief=case_brief,
                llm_client=llm_client,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            self._notify_stage(
                "extract_outline",
                "failure",
                error=str(exc),
            )
            raise
        state["outline_result"] = outline_result
        self._record_usage(state, "outline", outline_result.usage)
        outline_map: dict[str, Any] = outline_result.outline
        issue_count = sequence_length(outline_map.get("issues"))
        fact_count = sequence_length(outline_map.get("facts"))
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
        context_snippet = self._context_input_for_stage("analyze.build_timeline_seeds", state)
        outline_result: OutlineStageResult = state["outline_result"]
        case_brief: dict[str, Any] = state["case_brief"]
        runtime = self.stage_runtimes.get("analyze.build_timeline_seeds")
        llm_client = runtime.client if runtime else None
        max_tokens = (
            runtime.max_output_tokens
            if runtime and runtime.max_output_tokens
            else self.config.max_output_tokens
        )
        temperature = runtime.temperature if runtime else self.default_temperature
        self._notify_stage(
            "build_timeline_seeds",
            "start",
            provider=runtime.primary_provider if runtime else None,
            client_available=bool(llm_client),
        )
        try:
            outline_issues: list[dict[str, Any]] = coerce_mapping_list(
                outline_result.outline.get("issues")
            )
            timeline_result = generate_timeline(
                parse=parse,
                outline_issues=outline_issues,
                context_snippet=context_snippet,
                case_brief=case_brief,
                llm_client=llm_client,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            self._notify_stage(
                "build_timeline_seeds",
                "failure",
                error=str(exc),
            )
            raise
        state["timeline_result"] = timeline_result
        self._record_usage(state, "timeline", timeline_result.usage)
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
        context_snippet = self._context_input_for_stage("analyze.build_entity_hints", state)
        outline_result: OutlineStageResult = state["outline_result"]
        case_brief: dict[str, Any] = state["case_brief"]
        runtime = self.stage_runtimes.get("analyze.build_entity_hints")
        llm_client = runtime.client if runtime else None
        max_tokens = (
            runtime.max_output_tokens
            if runtime and runtime.max_output_tokens
            else self.config.max_output_tokens
        )
        temperature = runtime.temperature if runtime else self.default_temperature
        self._notify_stage(
            "build_entity_hints",
            "start",
            provider=runtime.primary_provider if runtime else None,
            client_available=bool(llm_client),
        )
        try:
            outline_parties: dict[str, Any] = coerce_mapping(outline_result.outline.get("parties"))
            entity_result = generate_entities(
                parse=parse,
                outline_parties=outline_parties,
                context_snippet=context_snippet,
                case_brief=case_brief,
                llm_client=llm_client,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            self._notify_stage(
                "build_entity_hints",
                "failure",
                error=str(exc),
            )
            raise
        state["entity_result"] = entity_result
        self._record_usage(state, "entities", entity_result.usage)
        entity_map: dict[str, Any] = entity_result.hints
        entities_count = sequence_length(entity_map.get("entities"))
        relations_count = sequence_length(entity_map.get("relations"))
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
        context_snippet = self._context_input_for_stage("analyze.draft_markdown", state)
        outline_result: OutlineStageResult = state["outline_result"]
        timeline_result: TimelineStageResult = state["timeline_result"]
        entity_result: EntityStageResult = state["entity_result"]
        case_brief: dict[str, Any] = state["case_brief"]
        runtime = self.stage_runtimes.get("analyze.draft_markdown")
        llm_client = runtime.client if runtime else None
        max_tokens = (
            runtime.max_output_tokens
            if runtime and runtime.max_output_tokens
            else self.config.max_output_tokens
        )
        temperature = runtime.temperature if runtime else self.default_temperature
        self._notify_stage(
            "draft_markdown",
            "start",
            provider=runtime.primary_provider if runtime else None,
            client_available=bool(llm_client),
        )
        try:
            summary_result = generate_summary_payload(
                parse=parse,
                outline=outline_result.outline,
                timeline=timeline_result.events,
                entities=entity_result.hints,
                intake=self.intake,
                context_snippet=context_snippet,
                case_brief=case_brief,
                llm_client=llm_client,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            self._notify_stage(
                "draft_markdown",
                "failure",
                error=str(exc),
            )
            raise
        state["summary_result"] = summary_result
        self._record_usage(state, "summary", summary_result.usage)
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
        summary_result: SummaryStageResult = state["summary_result"]
        markdown = summary_result.markdown.strip()
        markdown = self._ensure_header(markdown, parse)
        markdown = self._ensure_sections(markdown)
        state["summary_result"] = SummaryStageResult(
            data=summary_result.data,
            markdown=markdown,
            usage=summary_result.usage,
        )
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
        summary_result: SummaryStageResult = state["summary_result"]
        transcript_path: Path = state["transcript_path"]
        token_usage: dict[str, dict[str, int]] = state.get("token_usage", {})
        case_brief: dict[str, Any] = state.get("case_brief", {})
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
        )
        return state

    # Internal helpers -------------------------------------------------

    def _context_input_for_stage(self, stage_key: str, state: MutableMapping[str, Any]) -> Any:
        context_chunks: dict[str, list[str]] = state.get("context_chunks", {})
        chunks = context_chunks.get(stage_key)
        if not chunks:
            return state.get("context_snippet", "")
        if len(chunks) == 1:
            return chunks[0]
        if stage_key in {"analyze.draft_markdown", "analyze.qa_and_finalize"}:
            return chunks[0]
        return chunks

    def _collect_context_lines(self, parse: TranscriptParse) -> list[str]:
        lines: list[str] = []
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

    def _build_context_chunks_for_stage(self, stage_key: str, lines: list[str]) -> list[str]:
        if not lines:
            return [""]
        segment_limit = self._segment_limit()
        usable_lines = lines[:segment_limit] if segment_limit is not None else list(lines)
        if not usable_lines:
            usable_lines = lines
        char_limit = self._char_limit_for_stage(stage_key)
        if not char_limit or char_limit <= 0:
            return ["\n".join(usable_lines)]
        chunks: list[str] = []
        current: list[str] = []
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

    @staticmethod
    def _positive_int(value: object | None) -> int | None:
        if value is None:
            return None
        candidate: int
        if isinstance(value, bool):
            candidate = int(value)
        elif isinstance(value, int):
            candidate = value
        elif isinstance(value, float):
            candidate = int(value)
        elif isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            try:
                candidate = int(text)
            except ValueError:
                return None
        else:
            text = str(value).strip()
            if not text:
                return None
            try:
                candidate = int(text)
            except ValueError:
                return None
        return candidate if candidate > 0 else None

    def _segment_limit(self) -> int | None:
        override = self._positive_int(self.prompt_segments_override)
        if override is not None:
            return override
        config_limit = self._positive_int(getattr(self.config, "max_prompt_segments", None))
        return config_limit

    def _char_limit_for_stage(self, stage_key: str) -> int | None:
        runtime = self.stage_runtimes.get(stage_key)
        manual_limit = self._positive_int(self.prompt_chars_override)
        config_limit = self._positive_int(getattr(self.config, "max_prompt_chars", None))

        candidates: list[int] = []
        if manual_limit is not None:
            candidates.append(manual_limit)
        if config_limit is not None:
            candidates.append(config_limit)

        if runtime is None:
            return min(candidates) if candidates else None

        context_tokens = runtime.context_window_tokens
        if context_tokens is not None:
            available = context_tokens - runtime.profile.output_reserve_tokens
            bounded = max(available, runtime.profile.min_context_tokens)
        else:
            bounded = runtime.profile.recommended_context_tokens

        chunk_target = runtime.profile.target_chunk_tokens
        if chunk_target:
            bounded = min(bounded, chunk_target)

        char_limit = int(bounded * self.chars_per_token) if bounded else None
        if char_limit is not None and char_limit > 0:
            candidates.append(char_limit)

        return min(candidates) if candidates else None

    def _record_usage(
        self, state: MutableMapping[str, Any], stage: str, usage: dict[str, int]
    ) -> None:
        if not usage:
            return
        token_usage: dict[str, dict[str, int]] = state.setdefault("token_usage", {})
        token_usage[stage] = usage

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
    summary_result: SummaryStageResult,
    intake_payload: dict[str, Any],
    config: Any,
    token_usage: dict[str, dict[str, int]],
    case_brief: dict[str, Any],
    provider_chain: list[str] | None,
    transcript_hint: dict[str, Any] | None = None,
) -> FinalizedOutputs:
    analysis_dir = case_dir / "analysis"
    ops_dir = case_dir / "ops"
    ensure_dir(analysis_dir)
    ensure_dir(ops_dir)

    summary_json_path = next_versioned(analysis_dir / f"{job_id}__summary_v1.json")
    write_json_object(summary_json_path, summary_result.data)

    summary_markdown_path = next_versioned(analysis_dir / f"{job_id}__summary_v1.md")
    summary_markdown_path.write_text(summary_result.markdown, encoding="utf-8")

    outline_path = next_versioned(analysis_dir / f"{job_id}__outline_v1.json")
    write_json_object(outline_path, outline_result.outline)

    timeline_path = next_versioned(analysis_dir / f"{job_id}__timeline_seeds_v1.json")
    timeline_payload = {"events": timeline_result.events}
    write_json_object(timeline_path, timeline_payload)

    entity_path = next_versioned(analysis_dir / f"{job_id}__entity_hints_v1.json")
    write_json_object(entity_path, entity_result.hints)

    case_brief_payload = case_brief or {}
    case_brief_path = next_versioned(analysis_dir / f"{job_id}__case_brief_v1.json")
    write_json_object(case_brief_path, case_brief_payload)

    summary_json_sha = sha256_file(summary_json_path)
    summary_markdown_sha = sha256_file(summary_markdown_path)
    outline_sha = sha256_file(outline_path)
    timeline_sha = sha256_file(timeline_path)
    entity_sha = sha256_file(entity_path)
    case_brief_sha = sha256_file(case_brief_path)

    sha_map = {
        "summary_json": summary_json_sha,
        "summary_markdown": summary_markdown_sha,
        "outline": outline_sha,
        "timeline": timeline_sha,
        "entities": entity_sha,
        "case_brief": case_brief_sha,
    }

    words = len(summary_result.markdown.split())

    timestamp_utc = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

    facts_sequence = coerce_sequence(outline_result.outline.get("facts"))
    entities_sequence = coerce_sequence(entity_result.hints.get("entities"))

    sha_map_json = coerce_json_object(sha_map)

    meta: dict[str, Any] = {
        "case_id": case_id,
        "job_id": job_id,
        "source_transcript": str(transcript_path),
        "summary_file": summary_json_path.name,
        "summary_sha256": summary_json_sha,
        "summary_markdown_file": summary_markdown_path.name,
        "summary_markdown_sha256": summary_markdown_sha,
        "outline_file": outline_path.name,
        "outline_sha256": outline_sha,
        "timeline_seeds_file": timeline_path.name,
        "timeline_seeds_sha256": timeline_sha,
        "entity_hints_file": entity_path.name,
        "entity_hints_sha256": entity_sha,
        "case_brief_file": case_brief_path.name,
        "case_brief_sha256": case_brief_sha,
        "language": getattr(config, "language", "en-CA"),
        "timestamp_utc": timestamp_utc,
        "status": "ok",
        "words": words,
        "diarized": parse_diarized,
        "facts": len(facts_sequence) if facts_sequence is not None else 0,
        "timeline_events": len(timeline_result.events),
        "entity_count": len(entities_sequence) if entities_sequence is not None else 0,
        "udocket_core_version": UDOCKET_CORE_VERSION,
        "sha_map": sha_map_json,
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
    write_json_object(meta_path, meta)

    audit_path = ops_dir / "ops_summary.jsonl"
    append_jsonl(
        audit_path,
        {
            "ts": meta["timestamp_utc"],
            "case_id": case_id,
            "job_id": job_id,
            "event": "summary.created",
            "summary_file": str(summary_json_path),
            "summary_markdown_file": str(summary_markdown_path),
            "outline_file": str(outline_path),
            "timeline_file": str(timeline_path),
            "entity_file": str(entity_path),
            "case_brief_file": str(case_brief_path),
            "words": words,
            "providers": list(provider_chain or []),
            "udocket_core_version": UDOCKET_CORE_VERSION,
            "sha_map": sha_map_json,
        },
    )

    artifacts = {
        "summary": AnalysisArtifact("summary", summary_json_path, summary_json_sha, {}),
        "summary_markdown": AnalysisArtifact(
            "summary_markdown", summary_markdown_path, summary_markdown_sha, {}
        ),
        "outline": AnalysisArtifact("outline", outline_path, outline_sha, {}),
        "timeline": AnalysisArtifact("timeline", timeline_path, timeline_sha, {}),
        "entities": AnalysisArtifact("entities", entity_path, entity_sha, {}),
        "case_brief": AnalysisArtifact("case_brief", case_brief_path, case_brief_sha, {}),
    }

    return FinalizedOutputs(
        summary_path=summary_json_path,
        summary_markdown_path=summary_markdown_path,
        outline_path=outline_path,
        timeline_seed_path=timeline_path,
        entity_hint_path=entity_path,
        case_brief_path=case_brief_path,
        meta_path=meta_path,
        audit_path=audit_path,
        words=words,
        sha_map=sha_map,
        artifacts=artifacts,
        provider_chain=list(provider_chain or []),
    )


__all__ = ["FinalizedOutputs", "AnalyzePipeline", "finalize_outputs"]
