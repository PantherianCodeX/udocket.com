from __future__ import annotations

# pyright: strict

import json
import re
from typing import Mapping, Optional, Sequence, cast

from .utils.json import (
    JSONObject,
    JSONValue,
    coerce_float,
    coerce_json_object,
    coerce_object_list,
    coerce_str,
    coerce_str_list,
)

from .state import ComposeContext, ComposeInputs


def _coerce_optional_object(value: JSONValue) -> JSONObject:
    return coerce_json_object(value) if isinstance(value, Mapping) else {}


def _collect_alias_items(source: Mapping[str, JSONValue], *keys: str) -> list[JSONObject]:
    items: list[JSONObject] = []
    for key in keys:
        payload = source.get(key)
        if isinstance(payload, Mapping):
            items.append(coerce_json_object(payload))
        elif isinstance(payload, Sequence):
            for element in payload:
                if isinstance(element, Mapping):
                    items.append(coerce_json_object(element))
    return items


def _extract_parties(summary_data: Mapping[str, JSONValue]) -> list[JSONObject]:
    parties_value = summary_data.get("parties")
    parties: list[JSONObject] = []
    if isinstance(parties_value, Mapping):
        for role_key in (
            "client",
            "applicant",
            "plaintiff",
            "petitioner",
            "respondent",
            "defendant",
            "opposing",
        ):
            role_val = parties_value.get(role_key)
            if isinstance(role_val, Mapping):
                obj = coerce_json_object(role_val)
                obj.setdefault("role", role_key.upper())
                parties.append(obj)
        for collection_key in ("counsel", "lawyers", "representatives"):
            for item in coerce_object_list(parties_value.get(collection_key)):
                obj = coerce_json_object(item)
                obj.setdefault("role", collection_key[:-1].upper())
                parties.append(obj)
    elif isinstance(parties_value, Sequence):
        for element in parties_value:
            if isinstance(element, Mapping):
                parties.append(coerce_json_object(element))
    if not parties:
        parties.extend(_collect_alias_items(summary_data, "parties"))
    return parties


def _extract_deadlines(summary_data: Mapping[str, JSONValue]) -> list[JSONObject]:
    return _collect_alias_items(summary_data, "deadlines", "upcoming_deadlines")


def _extract_orders(summary_data: Mapping[str, JSONValue]) -> list[JSONObject]:
    orders = _collect_alias_items(summary_data, "orders", "orders_and_directions")
    if not orders:
        orders = _collect_alias_items(summary_data, "court_orders", "directions")
    return orders


def _extract_exhibits(summary_data: Mapping[str, JSONValue]) -> list[JSONObject]:
    return _collect_alias_items(summary_data, "exhibits", "evidence", "documents")


def _trim_atom(text: str) -> Optional[str]:
    normalized = text.strip()
    if not normalized or len(normalized) < 8:
        return None
    sanitized = re.sub(r"\s+", " ", normalized)
    return sanitized[:280]


def _collect_claimable_text(value: JSONValue, bucket: set[str]) -> None:
    if isinstance(value, str):
        trimmed = _trim_atom(value)
        if trimmed:
            bucket.add(trimmed)
        return
    if isinstance(value, Mapping):
        for child in value.values():
            _collect_claimable_text(child, bucket)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for element in value:
            _collect_claimable_text(element, bucket)


def assemble_context(inputs: ComposeInputs) -> ComposeContext:
    summary_data = inputs.summary_data
    parties = _extract_parties(summary_data)
    issues = _collect_alias_items(summary_data, "issues", "key_issues")
    facts = _collect_alias_items(summary_data, "facts", "key_facts")
    deadlines = _extract_deadlines(summary_data)
    orders = _extract_orders(summary_data)
    exhibits = _extract_exhibits(summary_data)

    events: list[JSONObject] = []
    for index, item in enumerate(inputs.timeline_seeds):
        event = coerce_json_object(item)
        event_id = coerce_str(event.get("id")) or f"event-{index + 1}"
        summary = coerce_str(event.get("summary")) or coerce_str(event.get("title")) or ""
        ts_start = coerce_float(event.get("ts_start"))
        ts_end = coerce_float(event.get("ts_end"))
        speakers = coerce_str_list(event.get("speakers"))
        references = coerce_str_list(event.get("references"))
        speakers_json = cast(list[JSONValue], list(speakers))
        references_json = cast(list[JSONValue], list(references))
        events.append(
            {
                "id": event_id,
                "summary": summary,
                "ts_start": ts_start,
                "ts_end": ts_end,
                "speakers": speakers_json,
                "references": references_json,
            }
        )

    for hint in coerce_object_list(inputs.entity_hints.get("entities")):
        parties.append(coerce_json_object(hint))

    claimable: set[str] = set()
    for fact in facts:
        text = coerce_str(fact.get("text")) or coerce_str(fact.get("summary")) or ""
        trimmed = _trim_atom(text)
        if trimmed:
            claimable.add(trimmed)
    for event in events:
        trimmed = _trim_atom(coerce_str(event.get("summary")) or "")
        if trimmed:
            claimable.add(trimmed)
    for deadline in deadlines:
        trimmed = _trim_atom(
            coerce_str(deadline.get("text")) or coerce_str(deadline.get("label")) or ""
        )
        if trimmed:
            claimable.add(trimmed)
    for order in orders:
        trimmed = _trim_atom(coerce_str(order.get("text")) or "")
        if trimmed:
            claimable.add(trimmed)

    for line in inputs.summary_markdown.splitlines():
        if line.strip().startswith("#"):
            continue
        trimmed = _trim_atom(line)
        if trimmed:
            claimable.add(trimmed)

    procedural = _coerce_optional_object(summary_data.get("procedural"))
    if inputs.intake:
        procedural = {**procedural, **inputs.intake}
    if inputs.case_metadata:
        procedural = {**procedural, **inputs.case_metadata}

    if inputs.intake:
        _collect_claimable_text(inputs.intake, claimable)
    if inputs.case_metadata:
        _collect_claimable_text(inputs.case_metadata, claimable)

    return ComposeContext(
        parties=parties,
        issues=issues,
        facts=facts,
        events=events,
        deadlines=deadlines,
        orders=orders,
        exhibits=exhibits,
        procedural=procedural,
        claimable_atoms=sorted(claimable),
    )


def serialize_context(context: ComposeContext) -> str:
    payload = {
        "parties": context.parties,
        "issues": context.issues,
        "facts": context.facts,
        "events": context.events,
        "deadlines": context.deadlines,
        "orders": context.orders,
        "exhibits": context.exhibits,
        "procedural": context.procedural,
        "claimable_atoms": context.claimable_atoms,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


__all__ = ["assemble_context", "serialize_context"]
