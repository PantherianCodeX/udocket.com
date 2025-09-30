from __future__ import annotations

import json
import logging
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, List, Optional, Sequence

from ...common.io import TranscriptParse
from ...common.chunking import (
    ChunkSplitConfig,
    should_retry_for_json,
    should_retry_for_length,
    split_for_retry,
)
from packages.udocket_core.llm.runtime import ChatClient

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

ENTITY_SPLIT_CONFIG = ChunkSplitConfig(min_lines=10, min_chars=2500)


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


def _ensure_chunks(context: Any) -> List[str]:
    if isinstance(context, str):
        return [context]
    if isinstance(context, Sequence):
        chunks: List[str] = []
        for item in context:
            if not isinstance(item, str):
                item = str(item)
            if item:
                chunks.append(item)
        return chunks or [""]
    return [str(context)]


def _merge_entity_payload(target: Dict[str, Any], update: Dict[str, Any]) -> None:
    existing_entities = target.setdefault("entities", [])
    update_entities = update.get("entities") or []
    if not isinstance(existing_entities, list) or not isinstance(update_entities, list):
        return

    def entity_key(entity: Dict[str, Any]) -> Any:
        return entity.get("id") or (entity.get("name"), entity.get("type"))

    index: Dict[Any, Dict[str, Any]] = {}
    for entity in existing_entities:
        index[entity_key(entity)] = entity

    for entity in update_entities:
        if not isinstance(entity, dict):
            continue
        key = entity_key(entity)
        existing = index.get(key)
        if existing is None:
            existing_entities.append(entity)
            index[key] = entity
            continue
        if entity.get("name") and not existing.get("name"):
            existing["name"] = entity["name"]
        if entity.get("type") and not existing.get("type"):
            existing["type"] = entity["type"]
        existing_aliases = existing.setdefault("aliases", [])
        if isinstance(existing_aliases, list):
            alias_seen = set(existing_aliases)
            for alias in entity.get("aliases") or []:
                if alias not in alias_seen:
                    existing_aliases.append(alias)
                    alias_seen.add(alias)
        existing_mentions = existing.setdefault("mentions", [])
        if isinstance(existing_mentions, list):
            mention_seen = {json.dumps(m, sort_keys=True) for m in existing_mentions}
            for mention in entity.get("mentions") or []:
                if not isinstance(mention, dict):
                    continue
                signature = json.dumps(mention, sort_keys=True)
                if signature not in mention_seen:
                    existing_mentions.append(mention)
                    mention_seen.add(signature)

    existing_relations = target.setdefault("relations", [])
    update_relations = update.get("relations") or []
    if isinstance(existing_relations, list) and isinstance(update_relations, list):
        relation_seen = {json.dumps(rel, sort_keys=True) for rel in existing_relations}
        for relation in update_relations:
            if not isinstance(relation, dict):
                continue
            signature = json.dumps(relation, sort_keys=True)
            if signature not in relation_seen:
                existing_relations.append(relation)
                relation_seen.add(signature)


def _merge_usage(target: Dict[str, int], usage: Dict[str, Any]) -> None:
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            target[key] = target.get(key, 0) + value



def generate_entities(
    *,
    parse: TranscriptParse,
    outline_parties: Dict[str, Any],
    context_snippet: Any,
    case_brief: Dict[str, Any],
    llm_client: Optional[ChatClient],
    temperature: float,
    max_tokens: int,
) -> EntityStageResult:
    if llm_client is None:
        raise RuntimeError("LLM client is required for entity stage")

    try:
        chunk_queue: Deque[str] = deque(_ensure_chunks(context_snippet))
        aggregate: Optional[Dict[str, Any]] = None
        usage_totals: Dict[str, int] = {}
        while chunk_queue:
            chunk_text = chunk_queue.popleft()
            if not chunk_text or not chunk_text.strip():
                continue
            system_prompt = (
                "You are an entity and relationship analyst for Canadian legal transcripts."
                " Extract people, organizations, locations, dockets, and relationships with evidence."
            )
            user_prompt = (
                "Use the outline and transcript snippets. Provide aliases where obvious."
                f"\nOutline parties: {json.dumps(outline_parties, ensure_ascii=False)}\n"
                f"\nCase brief summary: {json.dumps(case_brief, ensure_ascii=False)}\n"
                f"\nTranscript excerpts (remaining chunks: {len(chunk_queue)+1}):\n{chunk_text}\n"
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
                        "json_schema": {"name": "entity_v1", "schema": ENTITY_SCHEMA},
                    },
                )
            except RuntimeError as exc:
                if should_retry_for_length(str(exc)):
                    halves = split_for_retry(chunk_text, config=ENTITY_SPLIT_CONFIG)
                    if halves:
                        chunk_queue.appendleft(halves[1])
                        chunk_queue.appendleft(halves[0])
                        continue
                raise
            content_str = content.strip()
            if not content_str:
                logger.warning(
                    "Entity stage returned empty content; continuing with aggregated entities",
                )
                continue
            try:
                payload = json.loads(content_str)
            except json.JSONDecodeError as exc:
                logger.warning(
                    "Entity stage produced non-JSON payload; attempting to split chunk",
                )
                if should_retry_for_json(str(exc)) or should_retry_for_length(str(exc)):
                    halves = split_for_retry(chunk_text, config=ENTITY_SPLIT_CONFIG)
                    if halves:
                        chunk_queue.appendleft(halves[1])
                        chunk_queue.appendleft(halves[0])
                        continue
                continue
            if not isinstance(payload, dict):
                continue
            entities = payload.get("entities")
            if not isinstance(entities, list) or not entities:
                continue
            if aggregate is None:
                aggregate = payload
            else:
                _merge_entity_payload(aggregate, payload)
            _merge_usage(usage_totals, usage)
        if aggregate is None:
            raise RuntimeError("Entity stage returned no entities")
        return EntityStageResult(aggregate, usage_totals)
    except Exception as exc:
        raise RuntimeError(f"Entity stage failed: {exc}") from exc


__all__ = ["EntityStageResult", "generate_entities"]
