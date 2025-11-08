from __future__ import annotations

# pyright: strict
import json
import logging
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from textwrap import dedent
from typing import Any, cast

from packages.common.ids import ensure_deterministic_uuids
from packages.common.json_utils import (
    coerce_object_list,
    coerce_str_list,
    json_object_to_dict,
    parse_json_object,
)
from packages.common.prompts import (
    DEFAULT_LOCALE,
    PromptLogEntry,
    inline_prompt_entry,
)
from packages.common.text import prompt_lines, prompt_paragraphs

from ....llm.runtime import ChatClient, ResponseFormat
from ...common.chunking import (
    ChunkSplitConfig,
    should_retry_for_json,
    should_retry_for_length,
    split_for_retry,
)
from ...common.io import TranscriptParse
from ...common.normalization import coerce_mapping, coerce_mapping_list, coerce_sequence

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
    hints: dict[str, Any]
    usage: dict[str, int]
    prompts: tuple[PromptLogEntry, ...]


def _ensure_chunks(context: Any) -> list[str]:
    if isinstance(context, str):
        return [context]
    if isinstance(context, Sequence) and not isinstance(context, (str, bytes, bytearray)):
        sequence = cast(Sequence[object], context)
        chunks: list[str] = []
        for item in sequence:
            text = item if isinstance(item, str) else str(item)
            if text:
                chunks.append(text)
        return chunks or [""]
    return [str(context)]


def _assign_entity_defaults(entity: dict[str, Any]) -> dict[str, Any]:
    entity_obj = json_object_to_dict(entity)
    name = str(entity_obj.get("name") or "").strip()
    entity_type = str(entity_obj.get("type") or "UNKNOWN").strip() or "UNKNOWN"
    entity_obj["name"] = name
    entity_obj["type"] = entity_type
    entity_obj["aliases"] = coerce_str_list(entity_obj.get("aliases"), unique=True)
    entity_obj["_sig_name"] = name.lower()
    entity_obj["_sig_type"] = entity_type.lower()
    ensure_deterministic_uuids(
        [entity_obj],
        namespace="entity",
        signature_fields=("_sig_type", "_sig_name"),
    )
    entity_obj.pop("_sig_name", None)
    entity_obj.pop("_sig_type", None)
    entity_obj["id"] = entity_obj.get("id") or entity_obj["uuid"]

    normalized_mentions: list[dict[str, Any]] = []
    for mention_mapping in coerce_object_list(entity_obj.get("mentions")):
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
    entity_obj["mentions"] = normalized_mentions
    entity_obj.setdefault("description", "")
    return entity_obj


def _assign_relation_defaults(relation: dict[str, Any]) -> dict[str, Any]:
    relation_obj = json_object_to_dict(relation)
    relation_type = str(relation_obj.get("type") or "RELATED_TO").strip() or "RELATED_TO"
    source = str(relation_obj.get("source") or "").strip()
    target = str(relation_obj.get("target") or "").strip()
    relation_obj["type"] = relation_type
    relation_obj["source"] = source
    relation_obj["target"] = target
    relation_obj["_sig_type"] = relation_type.lower()
    relation_obj["_sig_source"] = source.lower()
    relation_obj["_sig_target"] = target.lower()
    ensure_deterministic_uuids(
        [relation_obj],
        namespace="relation",
        signature_fields=("_sig_type", "_sig_source", "_sig_target"),
    )
    relation_obj.pop("_sig_type", None)
    relation_obj.pop("_sig_source", None)
    relation_obj.pop("_sig_target", None)
    relation_obj["id"] = relation_obj.get("id") or relation_obj["uuid"]
    normalized_evidence: list[dict[str, Any]] = []
    for evidence_entry in coerce_object_list(relation_obj.get("evidence")):
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
    relation_obj["evidence"] = normalized_evidence
    return relation_obj


def _merge_entity_payload(target: dict[str, Any], update: dict[str, Any]) -> None:
    entities: list[dict[str, Any]] = [
        _assign_entity_defaults(json_object_to_dict(candidate))
        for candidate in coerce_object_list(target.get("entities"))
    ]
    target["entities"] = entities

    index: dict[str, dict[str, Any]] = {entity["id"]: entity for entity in entities}

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
        alias_list: list[str] = []
        for existing_alias in coerce_sequence(aliases_value) or []:
            if isinstance(existing_alias, str):
                alias_list.append(existing_alias)
        existing["aliases"] = alias_list
        alias_seen: set[str] = set(alias_list)
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
        mentions_list: list[dict[str, Any]] = []
        for existing_mention in coerce_sequence(mentions_value) or []:
            mention_dict = coerce_mapping(existing_mention)
            if not mention_dict:
                continue
            mentions_list.append(mention_dict)
        existing["mentions"] = mentions_list
        mention_seen: set[str] = {json.dumps(mention, sort_keys=True) for mention in mentions_list}
        for mention in coerce_mapping_list(normalized_entity.get("mentions")):
            if not mention:
                continue
            signature = json.dumps(mention, sort_keys=True)
            if signature in mention_seen:
                continue
            mentions_list.append(mention)
            mention_seen.add(signature)

    relations: list[dict[str, Any]] = [
        _assign_relation_defaults(json_object_to_dict(candidate))
        for candidate in coerce_object_list(target.get("relations"))
    ]
    target["relations"] = relations

    relation_seen: set[str] = {json.dumps(relation, sort_keys=True) for relation in relations}
    for relation_payload in coerce_object_list(update.get("relations")):
        normalized_relation = _assign_relation_defaults(json_object_to_dict(relation_payload))
        signature = json.dumps(normalized_relation, sort_keys=True)
        if signature in relation_seen:
            continue
        relations.append(normalized_relation)
        relation_seen.add(signature)


def _merge_usage(target: dict[str, int], usage: dict[str, Any]) -> None:
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            target[key] = target.get(key, 0) + value


def generate_entities(
    *,
    parse: TranscriptParse,
    outline_parties: dict[str, Any],
    context_snippet: Any,
    case_brief: dict[str, Any],
    llm_client: ChatClient | None,
    temperature: float,
    max_tokens: int,
    locale: str = DEFAULT_LOCALE,
) -> EntityStageResult:
    if llm_client is None:
        raise RuntimeError("LLM client is required for entity stage")

    try:
        chunk_queue: deque[str] = deque(_ensure_chunks(context_snippet))
        aggregate: dict[str, Any] | None = None
        usage_totals: dict[str, int] = {}
        prompt_records: dict[tuple[str, str], PromptLogEntry] = {}
        outline_json = json.dumps(outline_parties, ensure_ascii=False, indent=2)
        case_brief_json = json.dumps(case_brief, ensure_ascii=False, indent=2)

        while chunk_queue:
            chunk_text = chunk_queue.popleft()
            if not chunk_text or not chunk_text.strip():
                continue
            system_prompt = dedent(
                """\
                You are an entity and relationship analyst for Canadian legal transcripts.
                Extract people, organizations, locations, dockets, and relationships with evidence.
                """
            ).strip()
            remaining_chunks = len(chunk_queue) + 1
            user_prompt = prompt_paragraphs(
                prompt_lines(
                    "Use the outline and transcript snippets.",
                    "Provide aliases where obvious.",
                ),
                prompt_lines("Outline parties:", outline_json),
                prompt_lines("Case brief summary:", case_brief_json),
                prompt_lines(
                    f"Transcript excerpts (remaining chunks: {remaining_chunks}):",
                    chunk_text,
                ),
            )
            system_entry = inline_prompt_entry(
                domain="analyze",
                key="entities_system",
                locale=locale or DEFAULT_LOCALE,
                role="system",
                content=system_prompt,
            )
            prompt_records.setdefault(("system", system_entry.sha256), system_entry)
            user_entry = inline_prompt_entry(
                domain="analyze",
                key="entities_user",
                locale=locale or DEFAULT_LOCALE,
                role="user",
                content=user_prompt,
            )
            prompt_records.setdefault(("user", user_entry.sha256), user_entry)
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
        return EntityStageResult(aggregate, usage_totals, tuple(prompt_records.values()))
    except Exception as exc:
        raise RuntimeError(f"Entity stage failed: {exc}") from exc


__all__ = ["EntityStageResult", "generate_entities"]
