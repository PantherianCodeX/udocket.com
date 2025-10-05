from __future__ import annotations

# pyright: strict

import copy
import json
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Deque, cast

from ...common.chunking import (
    ChunkSplitConfig,
    should_retry_for_json,
    should_retry_for_length,
    split_for_retry,
)
from ...common.io import TranscriptParse
from packages.udocket_core.json_utils import (
    JSONObject,
    JSONValue,
    coerce_json_object,
    coerce_object_list,
    coerce_str,
    parse_json_object,
)
from packages.udocket_core.llm.runtime import ChatClient

OUTLINE_SCHEMA: JSONObject = {
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


@dataclass(frozen=True)
class OutlineStageResult:
    outline: JSONObject
    usage: dict[str, int]


def _outline_template(
    parse: TranscriptParse,
    intake: Mapping[str, JSONValue],
) -> JSONObject:
    client_name = coerce_str(intake.get("client_name"))
    opposing_name = coerce_str(intake.get("opposing_party"))
    client_role = coerce_str(intake.get("client_position"))

    issues: list[JSONObject] = []
    for idx, seg in enumerate(parse.segments[:5], start=1):
        issue: JSONObject = {
            "id": f"ISSUE-{idx}",
            "title": (seg.text[:80] or f"Issue {idx}").strip(),
            "description": seg.text,
            "stance_client": None,
            "stance_opposing": None,
            "status": "RAISED",
        }
        issues.append(issue)

    facts: list[JSONObject] = []
    for seg in parse.segments[:20]:
        fact: JSONObject = {
            "ts": seg.ts,
            "speaker": seg.speaker,
            "text": seg.text,
            "tags": ["transcript"],
        }
        facts.append(fact)

    outline: JSONObject = {
        "parties": {
            "client": {"name": client_name, "role": client_role},
            "opposing": {"name": opposing_name, "role": None},
            "counsel": cast(list[JSONValue], []),
        },
        "issues": cast(list[JSONValue], issues),
        "claims_and_remedies": cast(list[JSONValue], []),
        "facts": cast(list[JSONValue], facts),
        "deadlines": cast(list[JSONValue], []),
        "orders_and_directions": cast(list[JSONValue], []),
        "exhibits": cast(list[JSONValue], []),
        "legal_refs": cast(list[JSONValue], []),
    }
    return outline


def _coerce_outline(payload: Mapping[str, JSONValue], template: JSONObject) -> JSONObject:
    baseline: JSONObject = {key: copy.deepcopy(value) for key, value in template.items()}
    payload_obj = coerce_json_object(payload)
    for key, value in payload_obj.items():
        if key in baseline:
            baseline[key] = value
    return baseline


def _ensure_chunks(context: object) -> list[str]:
    if isinstance(context, str):
        return [context]
    if isinstance(context, Sequence) and not isinstance(context, (bytes, bytearray)):
        sequence = cast(Sequence[object], context)
        normalized: list[str] = []
        for item in sequence:
            text = item if isinstance(item, str) else str(item)
            if text.strip():
                normalized.append(text)
        return normalized or [""]
    return [str(context)]


def _merge_outline_sections(target: JSONObject, update: Mapping[str, JSONValue]) -> None:
    update_obj = coerce_json_object(update)

    def merge_object_list(key: str) -> None:
        additions: list[JSONObject] = coerce_object_list(update_obj.get(key))
        if not additions:
            return
        existing_value = target.get(key)
        existing_list: list[JSONValue]
        if isinstance(existing_value, list):
            existing_list = existing_value
        else:
            existing_list = []
            target[key] = existing_list
        seen = {
            json.dumps(item, sort_keys=True)
            for item in existing_list
            if isinstance(item, Mapping)
        }
        for item in additions:
            signature = json.dumps(item, sort_keys=True)
            if signature not in seen:
                existing_list.append(item)
                seen.add(signature)

    for section in (
        "issues",
        "claims_and_remedies",
        "facts",
        "deadlines",
        "orders_and_directions",
        "exhibits",
        "legal_refs",
    ):
        merge_object_list(section)

    parties_existing_value = target.get("parties")
    parties_target = coerce_json_object(parties_existing_value)
    target["parties"] = parties_target

    parties_update = coerce_json_object(update_obj.get("parties"))
    for party_key, payload in parties_update.items():
        payload_obj = coerce_json_object(payload)
        existing_payload_value = parties_target.get(party_key)
        existing_payload = coerce_json_object(existing_payload_value)
        parties_target[party_key] = existing_payload
        for attr_key, attr_value in payload_obj.items():
            if isinstance(attr_value, list):
                existing_value = existing_payload.get(attr_key)
                existing_list: list[JSONValue]
                if isinstance(existing_value, list):
                    existing_list = existing_value
                else:
                    existing_list = []
                    existing_payload[attr_key] = existing_list
                seen_aliases = {
                    json.dumps(item, sort_keys=True)
                    if isinstance(item, Mapping)
                    else str(item)
                    for item in existing_list
                }
                for item in attr_value:
                    signature = (
                        json.dumps(item, sort_keys=True)
                        if isinstance(item, Mapping)
                        else str(item)
                    )
                    if signature not in seen_aliases:
                        existing_list.append(item)
                        seen_aliases.add(signature)
            else:
                if attr_value and not existing_payload.get(attr_key):
                    existing_payload[attr_key] = attr_value


def _merge_usage(target: dict[str, int], usage: Mapping[str, object]) -> None:
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            target[key] = target.get(key, 0) + value


def generate_outline(
    *,
    parse: TranscriptParse,
    intake: Mapping[str, JSONValue],
    context_snippet: object,
    case_brief: Mapping[str, JSONValue],
    llm_client: ChatClient | None,
    temperature: float,
    max_tokens: int,
) -> OutlineStageResult:
    if llm_client is None:
        raise RuntimeError("LLM client is required for outline stage")

    try:
        template = _outline_template(parse, intake)
        chunk_queue: Deque[str] = deque(_ensure_chunks(context_snippet))
        aggregate_outline: JSONObject | None = None
        usage_totals: dict[str, int] = {}

        case_brief_payload = coerce_json_object(case_brief)
        intake_payload = coerce_json_object(intake)

        while chunk_queue:
            chunk_text: str = chunk_queue.popleft()
            if not chunk_text.strip():
                continue

            system_prompt = (
                "You are a Canadian paralegal assistant. Extract structured outline data from the provided"
                " transcript context. Only return JSON that matches the provided schema."
            )
            user_prompt = (
                "Case intake info (may be empty):\n"
                f"{json.dumps(intake_payload, ensure_ascii=False, indent=2)}\n\n"
                "Case brief summary:\n"
                f"{json.dumps(case_brief_payload, ensure_ascii=False, indent=2)}\n\n"
                f"Transcript excerpts (remaining chunks: {len(chunk_queue)+1}):\n{chunk_text}\n"
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
                        chunk_queue.appendleft(halves[1])
                        chunk_queue.appendleft(halves[0])
                        continue
                raise

            try:
                outline_payload = parse_json_object(content, context="outline stage payload")
            except ValueError as exc:
                if should_retry_for_json(str(exc)) or should_retry_for_length(str(exc)):
                    halves = split_for_retry(chunk_text, config=OUTLINE_SPLIT_CONFIG)
                    if halves:
                        chunk_queue.appendleft(halves[1])
                        chunk_queue.appendleft(halves[0])
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
    except Exception as exc:  # pragma: no cover - defensive guard
        raise RuntimeError(f"Outline stage failed: {exc}") from exc


__all__ = ["OutlineStageResult", "generate_outline"]
