from __future__ import annotations

# pyright: strict

import json
import logging
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, List, Mapping, Optional, Sequence, Set, cast
from uuid import NAMESPACE_URL, uuid5

from ...common.io import TranscriptParse
from ...common.chunking import (
    ChunkSplitConfig,
    should_retry_for_json,
    should_retry_for_length,
    split_for_retry,
)
from packages.udocket_core.json_utils import parse_json_object
from packages.udocket_core.llm.runtime import ChatClient

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
    aliases_raw = entity.get("aliases")
    alias_list: List[str] = []
    if isinstance(aliases_raw, Sequence) and not isinstance(aliases_raw, (str, bytes, bytearray)):
        for raw_alias in cast(Sequence[object], aliases_raw):
            alias_text = str(raw_alias).strip()
            if alias_text:
                alias_list.append(alias_text)
    elif isinstance(aliases_raw, str) and aliases_raw.strip():
        alias_list = [aliases_raw.strip()]
    entity["aliases"] = alias_list
    mentions = entity.get("mentions")
    mention_items: Sequence[object]
    if isinstance(mentions, Sequence) and not isinstance(mentions, (str, bytes, bytearray)):
        mention_items = cast(Sequence[object], mentions)
    else:
        mention_items = []
    normalized_mentions: List[Dict[str, Any]] = []
    for mention in mention_items:
        if not isinstance(mention, Mapping):
            continue
        mention_mapping = cast(Mapping[str, Any], mention)
        text = str(mention_mapping.get("text") or "").strip()
        if not text:
            continue
        ts = mention_mapping.get("ts")
        try:
            ts_val = float(ts) if ts is not None else None
        except (TypeError, ValueError):
            ts_val = None
        normalized_mentions.append({"ts": ts_val, "text": text})
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
    evidence = relation.get("evidence")
    if not isinstance(evidence, list):
        evidence = []
    normalized_evidence: List[Dict[str, Any]] = []
    for item in evidence:
        if isinstance(item, dict):
            text = str(item.get("text") or item.get("excerpt") or "").strip()
            if not text:
                continue
            ts_val = item.get("ts") or item.get("timestamp")
            try:
                ts = float(ts_val) if ts_val is not None else None
            except (TypeError, ValueError):
                ts = None
            normalized_evidence.append({"ts": ts, "text": text})
        elif isinstance(item, str) and item.strip():
            normalized_evidence.append({"ts": None, "text": item.strip()})
    relation["evidence"] = normalized_evidence
    relation["type"] = relation_type
    return relation


def _merge_entity_payload(target: Dict[str, Any], update: Dict[str, Any]) -> None:
    existing_entities_raw = target.get("entities")
    normalized_existing_entities: List[Dict[str, Any]] = []
    if isinstance(existing_entities_raw, list):
        for item in existing_entities_raw:
            if isinstance(item, dict):
                normalized_existing_entities.append(_assign_entity_defaults(item))
    target["entities"] = normalized_existing_entities

    index: Dict[str, Dict[str, Any]] = {entity["id"]: entity for entity in normalized_existing_entities}

    update_entities_raw = update.get("entities")
    if isinstance(update_entities_raw, Sequence):
        for entity_raw in update_entities_raw:
            if not isinstance(entity_raw, Mapping):
                continue
            normalized_entity = _assign_entity_defaults({str(key): value for key, value in entity_raw.items()})
            key = normalized_entity["id"]
            existing = index.get(key)
            if existing is None:
                normalized_existing_entities.append(normalized_entity)
                index[key] = normalized_entity
                continue
            if normalized_entity.get("name") and not existing.get("name"):
                existing["name"] = normalized_entity["name"]
            if normalized_entity.get("type") and not existing.get("type"):
                existing["type"] = normalized_entity["type"]
            existing_aliases = existing.setdefault("aliases", [])
            if isinstance(existing_aliases, list):
                alias_seen: Set[str] = set(existing_aliases)
                for alias in normalized_entity.get("aliases") or []:
                    if alias not in alias_seen:
                        existing_aliases.append(alias)
                        alias_seen.add(alias)
            existing_mentions = existing.setdefault("mentions", [])
            if isinstance(existing_mentions, list):
                mention_seen: Set[str] = {json.dumps(m, sort_keys=True) for m in existing_mentions}
                for mention in normalized_entity.get("mentions") or []:
                    if not isinstance(mention, dict):
                        continue
                    signature = json.dumps(mention, sort_keys=True)
                    if signature not in mention_seen:
                        existing_mentions.append(mention)
                        mention_seen.add(signature)

    existing_relations_raw = target.get("relations")
    normalized_relations: List[Dict[str, Any]] = []
    if isinstance(existing_relations_raw, list):
        for item in existing_relations_raw:
            if isinstance(item, dict):
                normalized_relations.append(_assign_relation_defaults(item))
    target["relations"] = normalized_relations

    relation_seen: Set[str] = {json.dumps(rel, sort_keys=True) for rel in normalized_relations}
    update_relations_raw = update.get("relations")
    if isinstance(update_relations_raw, Sequence):
        for relation_raw in update_relations_raw:
            if not isinstance(relation_raw, Mapping):
                continue
            normalized_relation = _assign_relation_defaults({str(key): value for key, value in relation_raw.items()})
            signature = json.dumps(normalized_relation, sort_keys=True)
            if signature in relation_seen:
                continue
            normalized_relations.append(normalized_relation)
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
