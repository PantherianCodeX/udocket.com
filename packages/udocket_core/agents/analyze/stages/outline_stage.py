from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, List, Optional, Sequence

import copy
import json

from ...common.io import TranscriptParse
from ...common.chunking import (
    ChunkSplitConfig,
    should_retry_for_json,
    should_retry_for_length,
    split_for_retry,
)
from packages.udocket_core.llm.runtime import ChatClient
from packages.udocket_core.json_utils import parse_json_object

OUTLINE_SCHEMA = {
    "type": "object",
    "properties": {
        "parties": {
            "type": "object",
            "properties": {
                "client": {
                    "type": "object",
                    "properties": {
                        "name": {"type": ["string", "null"]},
                        "role": {"type": ["string", "null"]},
                    },
                    "required": ["name", "role"],
                },
                "opposing": {
                    "type": "object",
                    "properties": {
                        "name": {"type": ["string", "null"]},
                        "role": {"type": ["string", "null"]},
                    },
                    "required": ["name", "role"],
                },
                "counsel": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "for": {"type": "string"},
                        },
                        "required": ["name", "for"],
                    },
                },
            },
            "required": ["client", "opposing", "counsel"],
        },
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "stance_client": {"type": ["string", "null"]},
                    "stance_opposing": {"type": ["string", "null"]},
                    "status": {"type": "string"},
                },
                "required": ["id", "title", "description", "status"],
            },
        },
        "claims_and_remedies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "remedy_requested": {"type": ["string", "null"]},
                    "amounts": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "jurisdictional_notes": {"type": ["string", "null"]},
                },
                "required": ["claim", "amounts"],
            },
        },
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ts": {"type": ["number", "null"]},
                    "speaker": {"type": ["string", "null"]},
                    "text": {"type": "string"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["text", "tags"],
            },
        },
        "deadlines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "date": {"type": ["string", "null"]},
                    "ts": {"type": ["number", "null"]},
                    "basis": {"type": ["string", "null"]},
                },
                "required": ["label"],
            },
        },
        "orders_and_directions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": ["string", "null"]},
                    "ts": {"type": ["number", "null"]},
                    "text": {"type": "string"},
                },
                "required": ["text"],
            },
        },
        "exhibits": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "description": {"type": "string"},
                    "cited_ts": {
                        "type": "array",
                        "items": {"type": "number"},
                    },
                },
                "required": ["id", "description", "cited_ts"],
            },
        },
        "legal_refs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "citation": {"type": "string"},
                    "context": {"type": "string"},
                },
                "required": ["citation", "context"],
            },
        },
    },
    "required": [
        "parties",
        "issues",
        "claims_and_remedies",
        "facts",
        "deadlines",
        "orders_and_directions",
        "exhibits",
        "legal_refs",
    ],
}

OUTLINE_SPLIT_CONFIG = ChunkSplitConfig(min_lines=10, min_chars=2500)


@dataclass
class OutlineStageResult:
    outline: Dict[str, Any]
    usage: Dict[str, int]


def _usage_dict(usage: Dict[str, Any]) -> Dict[str, int]:
    collector: Dict[str, int] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            collector[key] = value
    return collector


def _outline_template(parse: TranscriptParse, intake: Dict[str, Any]) -> Dict[str, Any]:
    client_name = intake.get("client_name")
    opposing = intake.get("opposing_party")
    client_role = intake.get("client_position")
    issues: List[Dict[str, Any]] = []
    for idx, seg in enumerate(parse.segments[:5], start=1):
        issues.append(
            {
                "id": f"ISSUE-{idx}",
                "title": seg.text[:80] or f"Issue {idx}",
                "description": seg.text,
                "stance_client": None,
                "stance_opposing": None,
                "status": "RAISED",
            }
        )
    facts: List[Dict[str, Any]] = []
    for seg in parse.segments[:20]:
        facts.append(
            {
                "ts": seg.ts,
                "speaker": seg.speaker,
                "text": seg.text,
                "tags": ["transcript"],
            }
        )
    return {
        "parties": {
            "client": {"name": client_name, "role": client_role},
            "opposing": {"name": opposing, "role": None},
            "counsel": [],
        },
        "issues": issues,
        "claims_and_remedies": [],
        "facts": facts,
        "deadlines": [],
        "orders_and_directions": [],
        "exhibits": [],
        "legal_refs": [],
    }


def _coerce_outline(payload: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {key: template.get(key) for key in template}
    if not isinstance(payload, dict):
        return merged
    for key in merged:
        value = payload.get(key)
        if value is not None:
            merged[key] = value
    return merged


def _ensure_chunks(context: Any) -> List[str]:
    if isinstance(context, str):
        return [context]
    if isinstance(context, Sequence):
        normalized: List[str] = []
        for item in context:
            if not isinstance(item, str):
                item = str(item)
            if item:
                normalized.append(item)
        return normalized or [""]
    return [str(context)]


def _merge_outline_sections(target: Dict[str, Any], update: Dict[str, Any]) -> None:
    def merge_list(key: str) -> None:
        existing = target.setdefault(key, [])
        incoming = update.get(key) or []
        if not isinstance(existing, list) or not isinstance(incoming, list):
            return
        seen = {json.dumps(item, sort_keys=True) for item in existing}
        for item in incoming:
            signature = json.dumps(item, sort_keys=True)
            if signature not in seen:
                existing.append(item)
                seen.add(signature)

    merge_list("issues")
    merge_list("claims_and_remedies")
    merge_list("facts")
    merge_list("deadlines")
    merge_list("orders_and_directions")
    merge_list("exhibits")
    merge_list("legal_refs")

    parties_existing = target.setdefault("parties", {})
    parties_update = update.get("parties", {})
    if isinstance(parties_existing, dict) and isinstance(parties_update, dict):
        for party_key, payload in parties_update.items():
            if not isinstance(payload, dict):
                continue
            existing_payload = parties_existing.setdefault(party_key, {})
            if not isinstance(existing_payload, dict):
                parties_existing[party_key] = payload
                continue
            for attr_key, attr_value in payload.items():
                if isinstance(attr_value, list):
                    existing_list = existing_payload.setdefault(attr_key, [])
                    if isinstance(existing_list, list):
                        seen = {json.dumps(item, sort_keys=True) for item in existing_list}
                        for item in attr_value:
                            signature = json.dumps(item, sort_keys=True)
                            if signature not in seen:
                                existing_list.append(item)
                                seen.add(signature)
                else:
                    if attr_value and not existing_payload.get(attr_key):
                        existing_payload[attr_key] = attr_value


def _merge_usage(target: Dict[str, int], usage: Dict[str, Any]) -> None:
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            target[key] = target.get(key, 0) + value


def generate_outline(
    *,
    parse: TranscriptParse,
    intake: Dict[str, Any],
    context_snippet: Any,
    case_brief: Dict[str, Any],
    llm_client: Optional[ChatClient],
    temperature: float,
    max_tokens: int,
) -> OutlineStageResult:
    if llm_client is None:
        raise RuntimeError("LLM client is required for outline stage")

    try:
        template = _outline_template(parse, intake)
        chunks: Deque[str] = deque(_ensure_chunks(context_snippet))
        aggregate_outline: Optional[Dict[str, Any]] = None
        usage_totals: Dict[str, int] = {}
        while chunks:
            chunk_text = chunks.popleft()
            if not chunk_text or not chunk_text.strip():
                continue
            lines = chunk_text.splitlines()
            system_prompt = (
                "You are a Canadian paralegal assistant. Extract structured outline data from the provided transcript"
                " context. Only return JSON that matches the provided schema."
            )
            user_prompt = (
                "Case intake info (may be empty):\n"
                f"{json.dumps(intake, ensure_ascii=False, indent=2)}\n\n"
                "Case brief summary:\n"
                f"{json.dumps(case_brief, ensure_ascii=False, indent=2)}\n\n"
                f"Transcript excerpts (remaining chunks: {len(chunks)+1}):\n" + chunk_text + "\n"
            )
            try:
                content, usage = llm_client.chat(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max(1, max_tokens),
                    response_format={
                        "type": "json_schema",
                        "json_schema": {"name": "outline_v1", "schema": OUTLINE_SCHEMA},
                    },
                )
            except RuntimeError as exc:
                message = str(exc)
                if should_retry_for_length(message):
                    halves = split_for_retry(chunk_text, config=OUTLINE_SPLIT_CONFIG)
                    if halves:
                        chunks.appendleft(halves[1])
                        chunks.appendleft(halves[0])
                        continue
                raise
            try:
                outline_payload = parse_json_object(content, context="outline stage payload")
            except ValueError as exc:
                if should_retry_for_json(str(exc)) or should_retry_for_length(str(exc)):
                    halves = split_for_retry(chunk_text, config=OUTLINE_SPLIT_CONFIG)
                    if halves:
                        chunks.appendleft(halves[1])
                        chunks.appendleft(halves[0])
                        continue
                preview = content.strip()[:200].replace("\n", " ")
                raise RuntimeError(
                    "Invalid JSON payload returned from outline stage: "
                    f"{exc}. Content preview: {preview!r}"
                ) from exc
            outline_chunk = _coerce_outline(outline_payload, template)
            if aggregate_outline is None:
                aggregate_outline = copy.deepcopy(outline_chunk)
            else:
                _merge_outline_sections(aggregate_outline, outline_chunk)
            _merge_usage(usage_totals, usage)
        if aggregate_outline is None:
            raise RuntimeError("Outline stage returned no data")
        return OutlineStageResult(aggregate_outline, usage_totals)
    except Exception as exc:
        raise RuntimeError(f"Outline stage failed: {exc}") from exc


__all__ = ["OutlineStageResult", "generate_outline"]
