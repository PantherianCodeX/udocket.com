from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import json

from ...common.io import TranscriptParse
from packages.udocket_core.llm.runtime import ChatClient
from packages.udocket_core.json_utils import parse_json_object


@dataclass
class SummaryStageResult:
    data: Dict[str, Any]
    markdown: str
    usage: Dict[str, int]


def _usage_dict(usage: Dict[str, Any]) -> Dict[str, int]:
    collector: Dict[str, int] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            collector[key] = value
    return collector


def generate_summary_payload(
    *,
    parse: TranscriptParse,
    outline: Dict[str, Any],
    timeline: List[Dict[str, Any]],
    entities: Dict[str, Any],
    intake: Dict[str, Any],
    context_snippet: Any,
    case_brief: Dict[str, Any],
    llm_client: Optional[ChatClient],
    temperature: float,
    max_tokens: int,
) -> SummaryStageResult:
    if llm_client is None:
        raise RuntimeError("LLM client is required for summary stage")

    try:
        if isinstance(context_snippet, (list, tuple)):
            context_snippet = context_snippet[0] if context_snippet else ""

        schema_description = {
            "case_metadata_summary": {
                "overview": "string",
                "parties": ["string"],
                "jurisdiction": "string",
                "key_dates": ["string"],
            },
            "executive_summary": {
                "bullets": ["string"],
            },
            "detailed_narrative": [
                {
                    "heading": "string",
                    "summary": "string",
                    "citations": ["string"],
                }
            ],
            "claims_and_remedies": [
                {
                    "claim": "string",
                    "remedy_requested": "string",
                }
            ],
            "procedural_posture": {
                "status": "string",
                "deadlines": ["string"],
                "orders": ["string"],
            },
            "risks_gaps_questions": [
                {
                    "issue": "string",
                    "risk_level": "low|medium|high",
                    "notes": "string",
                }
            ],
            "next_step_checklist": [
                {
                    "action": "string",
                    "owner": "string",
                    "due":"string",
                }
            ],
            "supporting_quotes": [
                {
                    "timestamp": "MM:SS",
                    "speaker": "string",
                    "text": "string",
                }
            ],
        }

        system_prompt = (
            "You are a compliance-focused summarization assistant supporting Canadian legal teams."
            " Produce a structured JSON object matching the provided schema exactly."
            " Never include legal advice, definitive interpretations, or form-selection guidance."
            " Flag any potentially risky content in the risks_gaps_questions section."
            " Respond with JSON only and no surrounding prose."
        )

        user_payload = {
            "intake": intake,
            "outline": outline,
            "timeline": timeline,
            "entities": entities,
            "case_brief": case_brief,
            "transcript_excerpt": context_snippet,
            "schema": schema_description,
        }

        content, usage = llm_client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            temperature=temperature,
            max_tokens=max(512, max_tokens),
            response_format={"type": "json_object"},
        )
        raw = (content or "").strip()
        data = _extract_json(raw)
        _validate_summary_schema(data)
        markdown = _render_markdown(data)
        return SummaryStageResult(data=data, markdown=markdown, usage=_usage_dict(usage))
    except Exception as exc:
        raise RuntimeError(f"Summary stage failed: {exc}") from exc


def _extract_json(raw: str) -> Dict[str, Any]:
    if not raw:
        raise RuntimeError("Summary stage returned no content")
    buffer = raw
    if "{" not in buffer:
        raise RuntimeError("Summary stage response was not JSON")
    start = buffer.find("{")
    end = buffer.rfind("}")
    candidate = buffer[start : end + 1]
    try:
        return parse_json_object(candidate, context="summary stage response")
    except ValueError as exc:
        raise RuntimeError(f"Unable to parse summary JSON: {exc}") from exc


def _validate_summary_schema(payload: Dict[str, Any]) -> None:
    required_top_keys = [
        "case_metadata_summary",
        "executive_summary",
        "detailed_narrative",
        "claims_and_remedies",
        "procedural_posture",
        "risks_gaps_questions",
        "next_step_checklist",
        "supporting_quotes",
    ]
    for key in required_top_keys:
        if key not in payload:
            raise RuntimeError(f"Summary JSON missing required field '{key}'")

    cms = payload.get("case_metadata_summary")
    if not isinstance(cms, dict):
        raise RuntimeError("case_metadata_summary must be an object")

    exec_summary = payload.get("executive_summary")
    if not isinstance(exec_summary, dict) or "bullets" not in exec_summary:
        raise RuntimeError("executive_summary must include a bullets array")

    for array_field in (
        "detailed_narrative",
        "claims_and_remedies",
        "risks_gaps_questions",
        "next_step_checklist",
        "supporting_quotes",
    ):
        value = payload.get(array_field)
        if value is None:
            raise RuntimeError(f"Summary JSON missing required array '{array_field}'")
        if not isinstance(value, list):
            raise RuntimeError(f"Summary JSON field '{array_field}' must be an array")


def _render_markdown(data: Dict[str, Any]) -> str:
    lines: List[str] = ["# Summary"]

    def _append_section(title: str, body: str) -> None:
        lines.append(f"\n## {title}\n{body.strip() if body else 'Pending.'}\n")

    cms = data.get("case_metadata_summary", {})
    overview = cms.get("overview") or "Pending case metadata."
    details: List[str] = []
    parties = cms.get("parties") or []
    if parties:
        details.append("**Parties:** " + ", ".join(parties))
    jurisdiction = cms.get("jurisdiction")
    if jurisdiction:
        details.append(f"**Jurisdiction:** {jurisdiction}")
    key_dates = cms.get("key_dates") or []
    if key_dates:
        details.append("**Key dates:** " + ", ".join(key_dates))
    _append_section("Case metadata summary", "\n".join([overview] + details))

    exec_summary = data.get("executive_summary", {}).get("bullets", [])
    bullets = "\n".join(f"- {item}" for item in exec_summary) or "- Pending executive summary."
    _append_section("Executive summary", bullets)

    narrative = data.get("detailed_narrative", [])
    narrative_lines = []
    for item in narrative:
        heading = item.get("heading") or "Narrative item"
        summary = item.get("summary") or "Pending summary."
        narrative_lines.append(f"- **{heading}:** {summary}")
    _append_section("Detailed narrative", "\n".join(narrative_lines) or "- Pending narrative.")

    claims = data.get("claims_and_remedies", [])
    claim_lines = []
    for item in claims:
        claim_lines.append(f"- {item.get('claim') or 'Claim'} — {item.get('remedy_requested') or 'Remedy'}")
    _append_section("Claims and remedies sought", "\n".join(claim_lines) or "- Pending claims.")

    posture = data.get("procedural_posture", {})
    posture_lines = []
    if posture.get("status"):
        posture_lines.append(f"**Status:** {posture['status']}")
    if posture.get("deadlines"):
        posture_lines.append("**Deadlines:** " + ", ".join(posture["deadlines"]))
    if posture.get("orders"):
        posture_lines.append("**Orders:** " + ", ".join(posture["orders"]))
    _append_section("Procedural posture, orders, and deadlines", "\n".join(posture_lines) or "Pending procedural posture.")

    risks = data.get("risks_gaps_questions", [])
    risk_lines = []
    for item in risks:
        risk_lines.append(
            f"- {item.get('issue') or 'Risk'} ({item.get('risk_level') or 'unspecified'}): {item.get('notes') or 'Pending details.'}"
        )
    _append_section("Risks, gaps, and questions", "\n".join(risk_lines) or "- Pending risk assessment.")

    steps = data.get("next_step_checklist", [])
    step_lines = []
    for item in steps:
        parts = [item.get("action") or "Action"]
        if item.get("owner"):
            parts.append(f"Owner: {item['owner']}")
        if item.get("due"):
            parts.append(f"Due: {item['due']}")
        step_lines.append("- " + "; ".join(parts))
    _append_section("Next-step checklist", "\n".join(step_lines) or "- Pending next steps.")

    quotes = data.get("supporting_quotes", [])
    quote_lines = []
    for quote in quotes:
        timestamp = quote.get("timestamp") or "--"
        speaker = quote.get("speaker") or "Speaker"
        text = quote.get("text") or "(no text)"
        quote_lines.append(f"- [{timestamp}] {speaker}: {text}")
    if quote_lines:
        _append_section("Supporting quotes", "\n".join(quote_lines))

    return "\n".join(lines).strip() + "\n"


__all__ = ["SummaryStageResult", "generate_summary_payload"]
