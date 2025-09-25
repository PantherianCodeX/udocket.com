from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import json

from ...common.azure_client import AzureChatClient
from ...common.io import TranscriptParse

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


def _fallback_timeline(parse: TranscriptParse) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for seg in parse.segments[:50]:
        events.append(
            {
                "ts_start": seg.ts,
                "ts_end": None,
                "speaker": seg.speaker,
                "text": seg.text,
                "labels": ["transcript"],
            }
        )
    return events


def generate_timeline(
    *,
    parse: TranscriptParse,
    outline_issues: List[Dict[str, Any]],
    context_snippet: str,
    azure_client: Optional[AzureChatClient],
    temperature: float,
    max_tokens: int,
) -> TimelineStageResult:
    fallback = _fallback_timeline(parse)
    if azure_client is None:
        return TimelineStageResult(fallback, {})

    try:
        system_prompt = (
            "You are a legal timeline analyst. Produce normalized events with start/end offsets (seconds),"
            " optional speakers, and descriptive labels."
        )
        user_prompt = (
            "Use these transcript excerpts to generate events. Ensure every object includes labels array.\n"
            f"Outline issues (for context): {json.dumps(outline_issues, ensure_ascii=False)}\n\n"
            + context_snippet
        )
        content, usage = azure_client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=min(max_tokens, 2000),
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "timeline_v1", "schema": TIMELINE_SCHEMA},
            },
        )
        payload = json.loads(content)
        events = payload.get("events", []) if isinstance(payload, dict) else []
        if not isinstance(events, list):
            return TimelineStageResult(fallback, {})
        normalized: List[Dict[str, Any]] = []
        for item in events:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "ts_start": item.get("ts_start"),
                    "ts_end": item.get("ts_end"),
                    "speaker": item.get("speaker"),
                    "text": item.get("text", ""),
                    "labels": list(item.get("labels") or []),
                }
            )
        if not normalized:
            return TimelineStageResult(fallback, {})
        return TimelineStageResult(normalized, _usage_dict(usage))
    except Exception:
        return TimelineStageResult(fallback, {})


__all__ = ["TimelineStageResult", "generate_timeline"]
