from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import json
import logging
from typing import Any, Deque, Dict, List, Optional, Sequence

from ...common.azure_client import AzureChatClient
from ...common.io import TranscriptParse
from ...common.chunking import (
    ChunkSplitConfig,
    should_retry_for_json,
    should_retry_for_length,
    split_for_retry,
)

logger = logging.getLogger("udocket.summarize.timeline_stage")

TIMELINE_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ts_start": {"type": ["number", "null"]},
                    "ts_end": {"type": ["number", "null"]},
                    "speaker": {"type": ["string", "null"]},
                    "text": {"type": "string"},
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["ts_start", "text", "labels"],
            },
        }
    },
    "required": ["events"],
}

TIMELINE_SPLIT_CONFIG = ChunkSplitConfig(min_lines=10, min_chars=2500)


@dataclass
class TimelineStageResult:
    events: List[Dict[str, Any]]
    usage: Dict[str, int]


def _usage_dict(usage: Dict[str, Any]) -> Dict[str, int]:
    collector: Dict[str, int] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            collector[key] = value
    return collector


def _ensure_chunks(context: Any) -> List[str]:
    if isinstance(context, str):
        return [context]
    if isinstance(context, Sequence):
        result: List[str] = []
        for item in context:
            if not isinstance(item, str):
                item = str(item)
            if item:
                result.append(item)
        return result or [""]
    return [str(context)]


def _merge_usage(target: Dict[str, int], usage: Dict[str, Any]) -> None:
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            target[key] = target.get(key, 0) + value


def generate_timeline(
    *,
    parse: TranscriptParse,
    outline_issues: List[Dict[str, Any]],
    context_snippet: Any,
    case_brief: Dict[str, Any],
    azure_client: Optional[AzureChatClient],
    temperature: float,
    max_tokens: int,
) -> TimelineStageResult:
    if azure_client is None:
        raise RuntimeError("Azure client is required for timeline stage")

    try:
        chunk_queue: Deque[str] = deque(_ensure_chunks(context_snippet))
        aggregated: List[Dict[str, Any]] = []
        usage_totals: Dict[str, int] = {}
        signatures = set()
        while chunk_queue:
            chunk_text = chunk_queue.popleft()
            if not chunk_text or not chunk_text.strip():
                continue
            system_prompt = (
                "You are a legal timeline analyst. Produce normalized events with start/end offsets (seconds),"
                " optional speakers, and descriptive labels."
            )
            user_prompt = (
                "Use these transcript excerpts to generate events. Ensure every object includes labels array.\n"
                f"Outline issues (for context): {json.dumps(outline_issues, ensure_ascii=False)}\n\n"
                f"Case brief summary: {json.dumps(case_brief, ensure_ascii=False)}\n\n"
                f"Transcript excerpts (remaining chunks: {len(chunk_queue)+1}):\n" + chunk_text
            )
            try:
                content, usage = azure_client.chat(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max(1, max_tokens),
                    response_format={
                        "type": "json_schema",
                        "json_schema": {"name": "timeline_v1", "schema": TIMELINE_SCHEMA},
                    },
                )
            except RuntimeError as exc:
                if should_retry_for_length(str(exc)):
                    halves = split_for_retry(chunk_text, config=TIMELINE_SPLIT_CONFIG)
                    if halves:
                        chunk_queue.appendleft(halves[1])
                        chunk_queue.appendleft(halves[0])
                        continue
                raise
            content_str = content.strip()
            if not content_str:
                logger.warning(
                    "Azure timeline stage returned empty content; continuing with aggregated results",
                )
                continue
            try:
                payload = json.loads(content_str)
            except json.JSONDecodeError as exc:
                logger.warning(
                    "Azure timeline stage produced non-JSON payload; skipping/splitting chunk",
                )
                if should_retry_for_json(str(exc)) or should_retry_for_length(str(exc)):
                    halves = split_for_retry(chunk_text, config=TIMELINE_SPLIT_CONFIG)
                    if halves:
                        chunk_queue.appendleft(halves[1])
                        chunk_queue.appendleft(halves[0])
                        continue
                continue
            events = payload.get("events", []) if isinstance(payload, dict) else []
            if not isinstance(events, list):
                continue
            for item in events:
                if not isinstance(item, dict):
                    continue
                normalized = {
                    "ts_start": item.get("ts_start"),
                    "ts_end": item.get("ts_end"),
                    "speaker": item.get("speaker"),
                    "text": item.get("text", ""),
                    "labels": list(item.get("labels") or []),
                }
                signature = (
                    normalized["ts_start"],
                    normalized["ts_end"],
                    normalized["speaker"],
                    normalized["text"],
                )
                if signature not in signatures:
                    aggregated.append(normalized)
                    signatures.add(signature)
            _merge_usage(usage_totals, usage)
        if not aggregated:
            raise RuntimeError("Azure timeline stage returned no events")
        return TimelineStageResult(aggregated, usage_totals)
    except Exception as exc:
        raise RuntimeError(f"Azure timeline stage failed: {exc}") from exc


__all__ = ["TimelineStageResult", "generate_timeline"]
