from __future__ import annotations

import json
import logging

# pyright: strict
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from packages.udocket_common.ids import ensure_deterministic_uuids, normalize_id
from packages.udocket_common.json_utils import parse_json_value

from ....llm.runtime import ChatClient, ResponseFormat
from ...common.chunking import (
    ChunkSplitConfig,
    should_retry_for_json,
    should_retry_for_length,
    split_for_retry,
)
from ...common.io import TranscriptParse
from ...common.normalization import coerce_mapping_list

logger = logging.getLogger("udocket.analyze.timeline_stage")

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
    events: list[dict[str, Any]]
    usage: dict[str, int]


def _ensure_chunks(context: Any) -> list[str]:
    if isinstance(context, str):
        return [context]
    if isinstance(context, Sequence) and not isinstance(context, (str, bytes, bytearray)):
        sequence = cast(Sequence[object], context)
        result: list[str] = []
        for item in sequence:
            text = item if isinstance(item, str) else str(item)
            if text:
                result.append(text)
        return result or [""]
    return [str(context)]


def _merge_usage(target: dict[str, int], usage: dict[str, Any]) -> None:
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            target[key] = target.get(key, 0) + value


def _normalize_event(payload: dict[str, Any]) -> dict[str, Any] | None:
    text = str(payload.get("text") or payload.get("summary") or "").strip()
    if not text:
        return None

    ts_start_raw = payload.get("ts_start")
    ts_end_raw = payload.get("ts_end")
    speaker_raw = payload.get("speaker")

    def _coerce_ts(value: Any) -> float | None:
        if value is None:
            return None
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None

    ts_start = _coerce_ts(ts_start_raw)
    ts_end = _coerce_ts(ts_end_raw)

    speaker = None
    if isinstance(speaker_raw, str):
        candidate = speaker_raw.strip()
        if candidate:
            speaker = candidate

    labels_raw = payload.get("labels")
    labels: list[str] = []
    if isinstance(labels_raw, (list, tuple)):
        for raw_label in cast(Sequence[object], labels_raw):
            label_text = str(raw_label).strip()
            if label_text:
                labels.append(label_text)
    elif isinstance(labels_raw, str) and labels_raw.strip():
        labels = [labels_raw.strip()]

    normalized: dict[str, Any] = {
        "id": normalize_id(payload.get("id")),
        "uuid": normalize_id(payload.get("uuid")),
        "ts_start": ts_start,
        "ts_end": ts_end,
        "speaker": speaker,
        "text": text,
        "labels": labels,
        "_sig_ts_start": "" if ts_start is None else f"{ts_start:.3f}",
        "_sig_ts_end": "" if ts_end is None else f"{ts_end:.3f}",
    }
    ensure_deterministic_uuids(
        [normalized],
        namespace="timeline.seed",
        signature_fields=("_sig_ts_start", "_sig_ts_end", "speaker", "text"),
    )
    normalized.pop("_sig_ts_start", None)
    normalized.pop("_sig_ts_end", None)
    normalized["id"] = normalized.get("id") or normalized["uuid"]
    return normalized


def generate_timeline(
    *,
    parse: TranscriptParse,
    outline_issues: list[dict[str, Any]],
    context_snippet: Any,
    case_brief: dict[str, Any],
    llm_client: ChatClient | None,
    temperature: float,
    max_tokens: int,
) -> TimelineStageResult:
    if llm_client is None:
        raise RuntimeError("LLM client is required for timeline stage")

    try:
        chunk_queue: deque[str] = deque(_ensure_chunks(context_snippet))
        aggregated: list[dict[str, Any]] = []
        usage_totals: dict[str, int] = {}
        signatures: set[tuple[str | None, float | None, float | None, str | None, str]] = (
            set()
        )
        while chunk_queue:
            chunk_text = chunk_queue.popleft()
            if not chunk_text or not chunk_text.strip():
                continue
            system_prompt = (
                "You are a legal timeline analyst."
                " Produce normalized events with start/end offsets (seconds), optional speakers,"
                " and descriptive labels."
            )
            remaining_chunks = len(chunk_queue) + 1
            outline_json = json.dumps(outline_issues, ensure_ascii=False)
            case_brief_json = json.dumps(case_brief, ensure_ascii=False)
            user_prompt = (
                "Use these transcript excerpts to generate events. Ensure every object includes "
                "labels array.\n"
                f"Outline issues (for context): {outline_json}\n\n"
                f"Case brief summary: {case_brief_json}\n\n"
                f"Transcript excerpts (remaining chunks: {remaining_chunks}):\n"
                f"{chunk_text}"
            )
            try:
                response_format = cast(
                    ResponseFormat,
                    {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "timeline_v1",
                            "schema": TIMELINE_SCHEMA,
                        },
                    },
                )
                content, usage = llm_client.chat(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max(1, max_tokens),
                    response_format=response_format,
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
                    "Timeline stage returned empty content; continuing with aggregated results",
                )
                continue
            payload = parse_json_value(content_str)
            if not isinstance(payload, Mapping):
                logger.warning(
                    "Timeline stage produced non-JSON payload; skipping chunk",
                )
                if should_retry_for_json("invalid json") or should_retry_for_length("invalid json"):
                    halves = split_for_retry(chunk_text, config=TIMELINE_SPLIT_CONFIG)
                    if halves:
                        chunk_queue.appendleft(halves[1])
                        chunk_queue.appendleft(halves[0])
                        continue
                continue
            events_raw = payload.get("events")
            if not isinstance(events_raw, list):
                continue
            for event_dict in coerce_mapping_list(events_raw):
                normalized = _normalize_event(event_dict)
                if normalized is None:
                    continue
                signature = (
                    normalized.get("uuid"),
                    normalized["ts_start"],
                    normalized["ts_end"],
                    normalized.get("speaker"),
                    normalized["text"],
                )
                if signature in signatures:
                    continue
                aggregated.append(normalized)
                signatures.add(signature)
            _merge_usage(usage_totals, usage)
        if not aggregated:
            raise RuntimeError("Timeline stage returned no events")
        return TimelineStageResult(aggregated, usage_totals)
    except Exception as exc:
        raise RuntimeError(f"Timeline stage failed: {exc}") from exc


__all__ = ["TimelineStageResult", "generate_timeline"]
