from __future__ import annotations

# pyright: strict
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from packages.udocket_common.json_utils import (
    JSONObject,
    JSONValue,
    coerce_json_object,
    coerce_object_list,
    coerce_str,
    coerce_str_list,
    parse_json_object,
)
from packages.udocket_common.prompts import (
    DEFAULT_LOCALE,
    PromptLogEntry,
    inline_prompt_entry,
)

from ....llm.runtime import ChatClient
from ...common.io import TranscriptParse
from ...common.normalization import coerce_sequence


@dataclass(frozen=True)
class SummaryStageResult:
    data: JSONObject
    markdown: str
    usage: dict[str, int]
    prompts: tuple[PromptLogEntry, ...]


def _usage_dict(usage: Mapping[str, object]) -> dict[str, int]:
    collector: dict[str, int] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            collector[key] = value
    return collector


def _normalize_snippet(snippet: object) -> str:
    if isinstance(snippet, str):
        return snippet
    for item in coerce_sequence(snippet) or []:
        text = item if isinstance(item, str) else str(item)
        if text.strip():
            return text
    if snippet is None:
        return ""
    return str(snippet)


def generate_summary_payload(
    *,
    parse: TranscriptParse,
    outline: Mapping[str, JSONValue],
    timeline: Sequence[Mapping[str, JSONValue]],
    entities: Mapping[str, JSONValue],
    intake: Mapping[str, JSONValue],
    context_snippet: object,
    case_brief: Mapping[str, JSONValue],
    llm_client: ChatClient | None,
    temperature: float,
    max_tokens: int,
    locale: str = DEFAULT_LOCALE,
) -> SummaryStageResult:
    if llm_client is None:
        raise RuntimeError("LLM client is required for summary stage")

    try:
        prompt_records: dict[tuple[str, str], PromptLogEntry] = {}

        schema_description: JSONObject = {
            "case_metadata_summary": {
                "overview": "string",
                "parties": ["string"],
                "jurisdiction": "string",
                "key_dates": ["string"],
            },
            "executive_summary": {"bullets": ["string"]},
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
                    "due": "string",
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

        snippet_text = _normalize_snippet(context_snippet)
        intake_payload = coerce_json_object(intake)
        outline_payload = coerce_json_object(outline)
        timeline_payload: list[JSONValue] = [coerce_json_object(mapping) for mapping in timeline]
        entities_payload = coerce_json_object(entities)
        case_brief_payload = coerce_json_object(case_brief)

        user_payload: JSONObject = {
            "intake": intake_payload,
            "outline": outline_payload,
            "timeline": timeline_payload,
            "entities": entities_payload,
            "case_brief": case_brief_payload,
            "transcript_excerpt": snippet_text,
            "schema": schema_description,
        }

        system_prompt = (
            "You are a compliance-focused summarization assistant supporting Canadian "
            "legal teams."
            " Produce a structured JSON object matching the provided schema exactly."
            " Never include legal advice, definitive interpretations, or "
            "form-selection guidance."
            " Flag any potentially risky content in the risks_gaps_questions section."
            " Respond with JSON only and no surrounding prose."
        )
        system_entry = inline_prompt_entry(
            domain="analyze",
            key="summary_system",
            locale=locale or DEFAULT_LOCALE,
            role="system",
            content=system_prompt,
        )
        prompt_records.setdefault(("system", system_entry.sha256), system_entry)
        user_prompt = json.dumps(user_payload, ensure_ascii=False)
        user_entry = inline_prompt_entry(
            domain="analyze",
            key="summary_user",
            locale=locale or DEFAULT_LOCALE,
            role="user",
            content=user_prompt,
        )
        prompt_records.setdefault(("user", user_entry.sha256), user_entry)

        content, usage = llm_client.chat(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=temperature,
            max_tokens=max(512, max_tokens),
            response_format={"type": "json_object"},
        )
        raw = content.strip()
        data = _extract_json(raw)
        _validate_summary_schema(data)
        markdown = _render_markdown(data)
        return SummaryStageResult(
            data=data,
            markdown=markdown,
            usage=_usage_dict(usage),
            prompts=tuple(prompt_records.values()),
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        raise RuntimeError(f"Summary stage failed: {exc}") from exc


def _extract_json(raw: str) -> JSONObject:
    if not raw:
        raise RuntimeError("Summary stage returned no content")
    if "{" not in raw:
        raise RuntimeError("Summary stage response was not JSON")
    start = raw.find("{")
    end = raw.rfind("}")
    candidate = raw[start : end + 1]
    try:
        return parse_json_object(candidate, context="summary stage response")
    except ValueError as exc:  # pragma: no cover - pass-through
        raise RuntimeError(f"Unable to parse summary JSON: {exc}") from exc


def _validate_summary_schema(payload: JSONObject) -> None:
    required_top_keys = (
        "case_metadata_summary",
        "executive_summary",
        "detailed_narrative",
        "claims_and_remedies",
        "procedural_posture",
        "risks_gaps_questions",
        "next_step_checklist",
        "supporting_quotes",
    )
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


def _render_markdown(data: JSONObject) -> str:
    lines: list[str] = ["# Summary"]

    def _append_section(title: str, body: str) -> None:
        trimmed = body.strip() if body else "Pending."
        lines.append(f"\n## {title}\n{trimmed}\n")

    cms_value = data.get("case_metadata_summary")
    cms = coerce_json_object(cms_value)
    overview = coerce_str(cms.get("overview")) or "Pending case metadata."
    details: list[str] = []
    parties = coerce_str_list(cms.get("parties"))
    if parties:
        details.append("**Parties:** " + ", ".join(parties))
    jurisdiction = coerce_str(cms.get("jurisdiction"))
    if jurisdiction:
        details.append(f"**Jurisdiction:** {jurisdiction}")
    key_dates = coerce_str_list(cms.get("key_dates"))
    if key_dates:
        details.append("**Key dates:** " + ", ".join(key_dates))
    metadata_body = overview
    if details:
        metadata_body += "\n\n" + "\n".join(f"- {item}" for item in details)
    _append_section("Case metadata summary", metadata_body)

    exec_summary_value = data.get("executive_summary")
    exec_summary = coerce_json_object(exec_summary_value)
    bullets = coerce_str_list(exec_summary.get("bullets"))
    bullet_body = (
        "\n".join(f"- {item}" for item in bullets) if bullets else "Pending executive summary."
    )
    _append_section("Executive summary", bullet_body)

    narrative = data.get("detailed_narrative")
    narrative_items: list[JSONObject] = coerce_object_list(narrative)
    narrative_lines: list[str] = []
    for item in narrative_items:
        heading = coerce_str(item.get("heading")) or "Section"
        summary = coerce_str(item.get("summary")) or "Pending summary paragraph."
        citations = coerce_str_list(item.get("citations"))
        block = f"**{heading}**\n{summary}"
        if citations:
            block += "\n" + "\n".join(f"  - {cite}" for cite in citations)
        narrative_lines.append(block)
    _append_section(
        "Detailed narrative",
        "\n\n".join(narrative_lines) if narrative_lines else "Pending narrative.",
    )

    claims = data.get("claims_and_remedies")
    claim_items: list[JSONObject] = coerce_object_list(claims)
    claim_lines: list[str] = []
    for item in claim_items:
        claim = coerce_str(item.get("claim")) or "Claim"
        remedy = coerce_str(item.get("remedy_requested")) or "Pending"
        claim_lines.append(f"- **{claim}:** {remedy}")
    _append_section(
        "Claims and remedies sought",
        "\n".join(claim_lines) if claim_lines else "Pending claims and remedies.",
    )

    posture_value = data.get("procedural_posture")
    posture = coerce_json_object(posture_value)
    status = coerce_str(posture.get("status")) or "Pending status update."
    deadlines = coerce_str_list(posture.get("deadlines"))
    orders = coerce_str_list(posture.get("orders"))
    posture_lines = [status]
    if deadlines:
        posture_lines.append("Deadlines: " + ", ".join(deadlines))
    if orders:
        posture_lines.append("Orders: " + ", ".join(orders))
    _append_section("Procedural posture, orders, and deadlines", "\n".join(posture_lines))

    risks_items: list[JSONObject] = coerce_object_list(data.get("risks_gaps_questions"))
    risk_lines: list[str] = []
    for item in risks_items:
        issue = coerce_str(item.get("issue")) or "Risk"
        level = (coerce_str(item.get("risk_level")) or "unknown").upper()
        notes = coerce_str(item.get("notes")) or "Pending notes."
        risk_lines.append(f"- **{issue} ({level})** — {notes}")
    _append_section(
        "Risks, gaps, and questions",
        "\n".join(risk_lines) if risk_lines else "Pending risk assessment.",
    )

    checklist_items: list[JSONObject] = coerce_object_list(data.get("next_step_checklist"))
    checklist_lines: list[str] = []
    for item in checklist_items:
        action = coerce_str(item.get("action")) or "Action"
        owner = coerce_str(item.get("owner")) or "Owner"
        due = coerce_str(item.get("due")) or "Pending"
        checklist_lines.append(f"- {action} (Owner: {owner}, Due: {due})")
    _append_section(
        "Next-step checklist",
        "\n".join(checklist_lines) if checklist_lines else "Pending next steps.",
    )

    quotes_items: list[JSONObject] = coerce_object_list(data.get("supporting_quotes"))
    quote_lines: list[str] = []
    for item in quotes_items:
        timestamp = coerce_str(item.get("timestamp")) or "--:--"
        speaker = coerce_str(item.get("speaker")) or "Unknown"
        text = coerce_str(item.get("text")) or ""
        quote_lines.append(f"- [{timestamp}] {speaker}: {text}")
    _append_section(
        "Supporting quotes", "\n".join(quote_lines) if quote_lines else "Pending supporting quotes."
    )

    return "".join(lines).strip()


__all__ = ["SummaryStageResult", "generate_summary_payload"]
