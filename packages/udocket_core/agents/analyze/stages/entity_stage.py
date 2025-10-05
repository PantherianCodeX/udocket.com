from __future__ import annotations

# pyright: strict

import json
import logging
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, List, Optional, Sequence, Set, cast
from uuid import NAMESPACE_URL, uuid5

from ...common.io import TranscriptParse
from ...common.normalization import coerce_mapping, coerce_mapping_list, coerce_sequence
from ...common.chunking import (
    ChunkSplitConfig,
    should_retry_for_json,
    should_retry_for_length,
    split_for_retry,
)
from packages.udocket_core.json_utils import (
    coerce_object_list,
    coerce_str_list,
    json_object_to_dict,
    parse_json_object,
)
from packages.udocket_core.llm.runtime import ChatClient, ResponseFormat

logger = logging.getLogger("udocket.analyze.entity_stage")

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


def _ensure_chunks(context: Any) -> List[str]:
    if isinstance(context, str):
        return [context]
    if isinstance(context, Sequence) and not isinstance(context, (str, bytes, bytearray)):
        sequence = cast(Sequence[object], context)
        chunks: List[str] = []
        for item in sequence:
            text = item if isinstance(item, str) else str(item)
            if text:
                chunks.append(text)
        return chunks or [""]
    return [str(context)]
def _assign_entity_defaults(entity: Dict[str, Any]) -> Dict[str, Any]:
    name = str(entity.get("name") or "").strip()
    entity_type = str(entity.get("type") or "UNKNOWN").strip() or "UNKNOWN"
    signature = f"entity|{entity_type}|{name.lower()}"
    derived_uuid = uuid5(NAMESPACE_URL, signature)
    existing_uuid = entity.get("uuid")
    entity_uuid = (
        str(existing_uuid).strip()
        if isinstance(existing_uuid, str) and existing_uuid.strip()
        else str(derived_uuid)
    )
    entity_id = str(entity.get("id") or entity_uuid or derived_uuid)
    entity["id"] = entity_id
    entity["uuid"] = entity_uuid
    entity["aliases"] = coerce_str_list(entity.get("aliases"), unique=True)

    normalized_mentions: List[Dict[str, Any]] = []
    for mention_mapping in coerce_object_list(entity.get("mentions")):
        raw_text = mention_mapping.get("text")
        if not isinstance(raw_text, str):
            raw_text = str(raw_text or "")
        text = raw_text.strip()
        if not text:
            continue
        ts_source = mention_mapping.get("ts")
        if ts_source is None:
            ts_source = mention_mapping.get("timestamp")
        ts_normalized: float | None
        if isinstance(ts_source, (int, float)):
            ts_normalized = float(ts_source)
        elif isinstance(ts_source, str):
            try:
                ts_normalized = float(ts_source)
            except ValueError:
                ts_normalized = None
        else:
            ts_normalized = None
        normalized_mentions.append({"ts": ts_normalized, "text": text})
    entity["mentions"] = normalized_mentions
    entity["type"] = entity_type
    entity.setdefault("description", "")
    return entity


def _assign_relation_defaults(relation: Dict[str, Any]) -> Dict[str, Any]:
    relation_type = str(relation.get("type") or "RELATED_TO").strip() or "RELATED_TO"
    source = str(relation.get("source") or "").strip()
    target = str(relation.get("target") or "").strip()
    signature = f"relation|{relation_type}|{source.lower()}|{target.lower()}"
    derived_uuid = uuid5(NAMESPACE_URL, signature)
    existing_uuid = relation.get("uuid")
    relation_uuid = (
        str(existing_uuid).strip()
        if isinstance(existing_uuid, str) and existing_uuid.strip()
        else str(derived_uuid)
    )
    relation_id = str(relation.get("id") or relation_uuid or derived_uuid)
    relation["id"] = relation_id
    relation["uuid"] = relation_uuid
    normalized_evidence: List[Dict[str, Any]] = []
    for evidence_entry in coerce_object_list(relation.get("evidence")):
        raw_text = evidence_entry.get("text") or evidence_entry.get("excerpt")
        if not isinstance(raw_text, str):
            raw_text = str(raw_text or "")
        text = raw_text.strip()
        if not text:
            continue
        ts_source = evidence_entry.get("ts")
        if ts_source is None:
            ts_source = evidence_entry.get("timestamp")
        ts_normalized: float | None
        if isinstance(ts_source, (int, float)):
            ts_normalized = float(ts_source)
        elif isinstance(ts_source, str):
            try:
                ts_normalized = float(ts_source)
            except ValueError:
                ts_normalized = None
        else:
            ts_normalized = None
        normalized_evidence.append({"ts": ts_normalized, "text": text})
    relation["evidence"] = normalized_evidence
    relation["type"] = relation_type
    return relation


def _merge_entity_payload(target: Dict[str, Any], update: Dict[str, Any]) -> None:
    entities: List[Dict[str, Any]] = [
        _assign_entity_defaults(json_object_to_dict(candidate))
        for candidate in coerce_object_list(target.get("entities"))
    ]
    target["entities"] = entities

    index: Dict[str, Dict[str, Any]] = {entity["id"]: entity for entity in entities}

    for entity_payload in coerce_object_list(update.get("entities")):
        normalized_entity = _assign_entity_defaults(json_object_to_dict(entity_payload))
        entity_id = normalized_entity["id"]
        existing = index.get(entity_id)
        if existing is None:
            entities.append(normalized_entity)
            index[entity_id] = normalized_entity
            existing = normalized_entity
        else:
            if normalized_entity.get("name") and not existing.get("name"):
                existing["name"] = normalized_entity["name"]
            if normalized_entity.get("type") and not existing.get("type"):
                existing["type"] = normalized_entity["type"]

        aliases_value = existing.setdefault("aliases", [])
        alias_list: List[str] = []
        for existing_alias in coerce_sequence(aliases_value) or []:
            if isinstance(existing_alias, str):
                alias_list.append(existing_alias)
        existing["aliases"] = alias_list
        alias_seen: Set[str] = set(alias_list)
        normalized_aliases = coerce_sequence(normalized_entity.get("aliases")) or []
        for raw_alias in normalized_aliases:
            if not isinstance(raw_alias, str):
                continue
            alias = raw_alias.strip()
            if not alias or alias in alias_seen:
                continue
            alias_list.append(alias)
            alias_seen.add(alias)

        mentions_value = existing.setdefault("mentions", [])
        mentions_list: List[Dict[str, Any]] = []
        for existing_mention in coerce_sequence(mentions_value) or []:
            mention_dict = coerce_mapping(existing_mention)
            if not mention_dict:
                continue
            mentions_list.append(mention_dict)
        existing["mentions"] = mentions_list
        mention_seen: Set[str] = {
            json.dumps(mention, sort_keys=True)
            for mention in mentions_list
        }
        for mention in coerce_mapping_list(normalized_entity.get("mentions")):
            if not mention:
                continue
            signature = json.dumps(mention, sort_keys=True)
            if signature in mention_seen:
                continue
            mentions_list.append(mention)
            mention_seen.add(signature)

    relations: List[Dict[str, Any]] = [
        _assign_relation_defaults(json_object_to_dict(candidate))
        for candidate in coerce_object_list(target.get("relations"))
    ]
    target["relations"] = relations

    relation_seen: Set[str] = {json.dumps(relation, sort_keys=True) for relation in relations}
    for relation_payload in coerce_object_list(update.get("relations")):
        normalized_relation = _assign_relation_defaults(json_object_to_dict(relation_payload))
        signature = json.dumps(normalized_relation, sort_keys=True)
        if signature in relation_seen:
            continue
        relations.append(normalized_relation)
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
                response_format = cast(
                    ResponseFormat,
                    {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "entity_v1",
                            "schema": ENTITY_SCHEMA,
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
                payload = parse_json_object(content_str, context="entity stage payload")
            except ValueError as exc:
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
            entities = payload.get("entities")
            if not isinstance(entities, list) or not entities:
                continue
            if aggregate is None:
                aggregate = {"entities": [], "relations": []}
            _merge_entity_payload(aggregate, payload)
            _merge_usage(usage_totals, usage)
        if aggregate is None:
            raise RuntimeError("Entity stage returned no entities")
        return EntityStageResult(aggregate, usage_totals)
    except Exception as exc:
        raise RuntimeError(f"Entity stage failed: {exc}") from exc


__all__ = ["EntityStageResult", "generate_entities"]
