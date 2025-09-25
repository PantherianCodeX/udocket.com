from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import json

from ...common.azure_client import AzureChatClient
from ...common.io import TranscriptParse

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


def _fallback_outline(parse: TranscriptParse, intake: Dict[str, Any]) -> Dict[str, Any]:
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


def _coerce_outline(payload: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {key: fallback.get(key) for key in fallback}
    if not isinstance(payload, dict):
        return merged
    for key in merged:
        value = payload.get(key)
        if value is not None:
            merged[key] = value
    return merged


def generate_outline(
    *,
    parse: TranscriptParse,
    intake: Dict[str, Any],
    context_snippet: str,
    azure_client: Optional[AzureChatClient],
    temperature: float,
    max_tokens: int,
) -> OutlineStageResult:
    fallback = _fallback_outline(parse, intake)
    if azure_client is None:
        return OutlineStageResult(fallback, {})

    try:
        system_prompt = (
            "You are a Canadian paralegal assistant. Extract structured outline data from the provided transcript"
            " context. Only return JSON that matches the provided schema."
        )
        user_prompt = (
            "Case intake info (may be empty):\n"
            f"{json.dumps(intake, ensure_ascii=False, indent=2)}\n\n"
            "Transcript excerpts:\n" + context_snippet + "\n"
        )
        content, usage = azure_client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=min(max_tokens, 3000),
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "outline_v1", "schema": OUTLINE_SCHEMA},
            },
        )
        outline = _coerce_outline(json.loads(content), fallback)
        return OutlineStageResult(outline, _usage_dict(usage))
    except Exception:
        return OutlineStageResult(fallback, {})


__all__ = ["OutlineStageResult", "generate_outline"]
