from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .common import (
    AzureChatClient,
    AzureClientConfig,
    append_jsonl,
    ensure_dir,
    next_versioned,
    parse_transcript,
    sha256_file,
    TranscriptParse,
)
from .common.azure_client import _endpoint_is_canadian
from .common.io import TranscriptSegment  # re-export for legacy imports
from .summarize.stages import (
    DraftStageResult,
    EntityStageResult,
    OutlineStageResult,
    TimelineStageResult,
    generate_entities,
    generate_outline,
    generate_summary_markdown,
    generate_timeline,
)

MAX_PROMPT_SEGMENTS = 120
MAX_PROMPT_CHARS = 8000


def _now_utc() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


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
    ) -> SummarizeResult:
        case_dir = Path(case_dir)
        transcript_path = self._resolve_transcript(input, case_dir)
        parse = parse_transcript(transcript_path)

        summary_dir = case_dir / "analysis"
        ops_dir = case_dir / "ops"
        ensure_dir(summary_dir)
        ensure_dir(ops_dir)

        azure_client = None
        azure_cfg = self.config.azure_client_config()
        if azure_cfg is not None:
            azure_client = AzureChatClient(azure_cfg)

        intake_payload = intake or {}
        context_snippet = self._build_context(parse, intake_payload)

        outline_result = generate_outline(
            parse=parse,
            intake=intake_payload,
            context_snippet=context_snippet,
            azure_client=azure_client,
            temperature=self.config.temperature,
            max_tokens=self.config.max_output_tokens,
        )

        timeline_result = generate_timeline(
            parse=parse,
            outline_issues=outline_result.outline.get("issues", []),
            context_snippet=context_snippet,
            azure_client=azure_client,
            temperature=self.config.temperature,
            max_tokens=self.config.max_output_tokens,
        )

        entity_result = generate_entities(
            parse=parse,
            outline_parties=outline_result.outline.get("parties", {}),
            context_snippet=context_snippet,
            azure_client=azure_client,
            temperature=self.config.temperature,
            max_tokens=self.config.max_output_tokens,
        )

        summary_result = generate_summary_markdown(
            parse=parse,
            outline=outline_result.outline,
            timeline=timeline_result.events,
            entities=entity_result.hints,
            intake=intake_payload,
            context_snippet=context_snippet,
            azure_client=azure_client,
            temperature=self.config.temperature,
            max_tokens=self.config.max_output_tokens,
        )

        summary_path = next_versioned(summary_dir / f"{job_id}__summary_v1.md")
        summary_path.write_text(summary_result.markdown, encoding="utf-8")

        outline_path = next_versioned(summary_dir / f"{job_id}__outline_v1.json")
        outline_path.write_text(json.dumps(outline_result.outline, ensure_ascii=False, indent=2), encoding="utf-8")

        timeline_path = next_versioned(summary_dir / f"{job_id}__timeline_seeds_v1.json")
        timeline_payload = {"events": timeline_result.events}
        timeline_path.write_text(json.dumps(timeline_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        entity_path = next_versioned(summary_dir / f"{job_id}__entity_hints_v1.json")
        entity_path.write_text(json.dumps(entity_result.hints, ensure_ascii=False, indent=2), encoding="utf-8")

        summary_sha = sha256_file(summary_path)
        outline_sha = sha256_file(outline_path)
        timeline_sha = sha256_file(timeline_path)
        entity_sha = sha256_file(entity_path)

        token_usage: Dict[str, Dict[str, int]] = {}
        if outline_result.usage:
            token_usage["outline"] = outline_result.usage
        if timeline_result.usage:
            token_usage["timeline"] = timeline_result.usage
        if entity_result.usage:
            token_usage["entities"] = entity_result.usage
        if summary_result.usage:
            token_usage["summary"] = summary_result.usage

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
            "language": self.config.language,
            "azure_enabled": self.config.azure_enabled,
            "azure_region": self.config.azure_region,
            "timestamp_utc": _now_utc(),
            "status": "ok",
            "words": len(summary_result.markdown.split()),
            "diarized": parse.diarized,
            "facts": len(outline_result.outline.get("facts", [])),
            "timeline_events": len(timeline_result.events),
            "entity_count": len(entity_result.hints.get("entities", [])),
        }
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
                "ts": _now_utc(),
                "case_id": case_id,
                "job_id": job_id,
                "event": "summary.created",
                "summary_file": str(summary_path),
                "outline_file": str(outline_path),
                "timeline_file": str(timeline_path),
                "entity_file": str(entity_path),
                "words": meta["words"],
            },
        )

        return SummarizeResult(
            status="ok",
            summary_file=summary_path,
            outline_file=outline_path,
            timeline_seeds_file=timeline_path,
            entity_hints_file=entity_path,
            words=meta["words"],
            source_transcript=transcript_path,
            meta_json=meta_path,
            audit_jsonl=audit_path,
        )

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
    "TranscriptParse",
    "TranscriptSegment",
]
