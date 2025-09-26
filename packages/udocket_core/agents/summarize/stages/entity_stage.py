from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ...common.azure_client import AzureChatClient
from ...common.io import TranscriptParse
from ..exceptions import AzureStageFailure

logger = logging.getLogger("udocket.summarize.entity_stage")

ENTITY_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "aliases": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "mentions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ts": {"type": ["number", "null"]},
                                "text": {"type": "string"},
                            },
                            "required": ["text"],
                        },
                    },
                },
                "required": ["id", "name", "type", "aliases"],
            },
        },
        "relations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ts": {"type": ["number", "null"]},
                                "text": {"type": "string"},
                            },
                            "required": ["text"],
                        },
                    },
                },
                "required": ["type", "source", "target", "evidence"],
            },
        },
    },
    "required": ["entities", "relations"],
}


@dataclass
class EntityStageResult:
    hints: Dict[str, Any]
    usage: Dict[str, int]


def _usage_dict(usage: Dict[str, Any]) -> Dict[str, int]:
    collector: Dict[str, int] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            collector[key] = value
    return collector


def _fallback_entities(parse: TranscriptParse) -> Dict[str, Any]:
    speakers = {seg.speaker for seg in parse.segments if seg.speaker}
    entities = []
    for idx, speaker in enumerate(sorted(speakers or {"SPK"}), start=1):
        entities.append(
            {
                "id": f"E{idx}",
                "name": speaker,
                "type": "PERSON",
                "aliases": [],
                "mentions": [],
            }
        )
    return {"entities": entities, "relations": []}


def generate_entities(
    *,
    parse: TranscriptParse,
    outline_parties: Dict[str, Any],
    context_snippet: str,
    case_brief: Dict[str, Any],
    azure_client: Optional[AzureChatClient],
    temperature: float,
    max_tokens: int,
) -> EntityStageResult:
    fallback = _fallback_entities(parse)
    if azure_client is None:
        return EntityStageResult(fallback, {})

    try:
        system_prompt = (
            "You are an entity and relationship analyst for Canadian legal transcripts."
            " Extract people, organizations, locations, dockets, and relationships with evidence."
        )
        user_prompt = (
            "Use the outline and transcript snippets. Provide aliases where obvious."
            f"\nOutline parties: {json.dumps(outline_parties, ensure_ascii=False)}\n"
            f"\nCase brief summary: {json.dumps(case_brief, ensure_ascii=False)}\n"
            f"\nTranscript excerpts:\n{context_snippet}\n"
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
                "json_schema": {"name": "entity_v1", "schema": ENTITY_SCHEMA},
            },
        )
        content_str = content.strip()
        if not content_str:
            logger.warning(
                "Azure entity stage returned empty content; falling back to heuristic entities",
            )
            return EntityStageResult(fallback, _usage_dict(usage))
        try:
            payload = json.loads(content_str)
        except json.JSONDecodeError:
            logger.warning(
                "Azure entity stage produced non-JSON payload; falling back to heuristic entities",
            )
            return EntityStageResult(fallback, _usage_dict(usage))
        if not isinstance(payload, dict):
            return EntityStageResult(fallback, {})
        entities = payload.get("entities")
        if not isinstance(entities, list) or not entities:
            return EntityStageResult(fallback, {})
        return EntityStageResult(payload, _usage_dict(usage))
    except Exception as exc:
        raise AzureStageFailure("entities", exc, EntityStageResult(fallback, {})) from exc


__all__ = ["EntityStageResult", "generate_entities"]
