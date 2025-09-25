from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import json

from ...common.azure_client import AzureChatClient
from ...common.io import TranscriptParse


@dataclass
class DraftStageResult:
    markdown: str
    usage: Dict[str, int]


def _usage_dict(usage: Dict[str, Any]) -> Dict[str, int]:
    collector: Dict[str, int] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            collector[key] = value
    return collector


def _fallback_markdown(
    parse: TranscriptParse,
    outline: Dict[str, Any],
    timeline: List[Dict[str, Any]],
    entities: Dict[str, Any],
    intake: Dict[str, Any],
) -> str:
    lines: List[str] = ["# Summarize output", ""]
    if intake:
        lines.append("## Case metadata")
        for key, value in intake.items():
            lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
        lines.append("")
    lines.append("## Executive summary")
    lines.append("- Offline fallback summary generated without Azure OpenAI.")
    lines.append("- Configure Azure credentials for richer analysis.")
    lines.append("")
    lines.append("## Detailed narrative")
    for seg in parse.segments[:10]:
        prefix = ""
        if seg.ts is not None:
            minutes = int(seg.ts // 60)
            seconds = int(seg.ts % 60)
            prefix = f"[{minutes:02d}:{seconds:02d}] "
        speaker = f"{seg.speaker}: " if seg.speaker else ""
        lines.append(f"- {prefix}{speaker}{seg.text}")
    lines.append("")
    lines.append("## Claims and remedies")
    if outline.get("claims_and_remedies"):
        for claim in outline["claims_and_remedies"]:
            lines.append(f"- {claim.get('claim', 'Unknown claim')}")
    else:
        lines.append("- Not available in offline mode.")
    lines.append("")
    lines.append("## Procedural posture, orders, and deadlines")
    if outline.get("orders_and_directions"):
        for order in outline["orders_and_directions"]:
            lines.append(f"- {order.get('text', '')}")
    else:
        lines.append("- Not available in offline mode.")
    lines.append("")
    lines.append("## Risks, gaps, questions")
    lines.append("- Review transcript manually to confirm key issues.")
    lines.append("- Verify filing deadlines in court records.")
    lines.append("")
    lines.append("## Next-step checklist")
    lines.append("- Configure Azure OpenAI for full summarize pipeline.")
    lines.append("- Confirm transcript approval status before sharing.")
    lines.append("")
    lines.append("_Offline fallback summary. Configure Azure OpenAI for richer outputs._")
    lines.append("")
    return "\n".join(lines)


def generate_summary_markdown(
    *,
    parse: TranscriptParse,
    outline: Dict[str, Any],
    timeline: List[Dict[str, Any]],
    entities: Dict[str, Any],
    intake: Dict[str, Any],
    context_snippet: str,
    azure_client: Optional[AzureChatClient],
    temperature: float,
    max_tokens: int,
) -> DraftStageResult:
    fallback = _fallback_markdown(parse, outline, timeline, entities, intake)
    if azure_client is None:
        return DraftStageResult(fallback, {})

    try:
        system_prompt = (
            "You are a Canadian paralegal writing a layered legal summary for colleagues preparing court forms."
            " Include required sections: Case metadata, Executive summary (bullets), Detailed narrative,"
            " Claims and remedies, Procedural posture, Risks/gaps/questions, Next-step checklist."
            " Reference transcript timestamps in [mm:ss] format where relevant."
        )
        user_prompt = (
            "Case intake info:\n"
            f"{json.dumps(intake, ensure_ascii=False, indent=2)}\n\n"
            "Structured outline:\n"
            f"{json.dumps(outline, ensure_ascii=False, indent=2)}\n\n"
            "Timeline seeds:\n"
            f"{json.dumps(timeline, ensure_ascii=False, indent=2)}\n\n"
            "Entity hints:\n"
            f"{json.dumps(entities, ensure_ascii=False, indent=2)}\n\n"
            "Transcript excerpts:\n"
            f"{context_snippet}\n"
        )
        content, usage = azure_client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=min(max_tokens, 4000),
        )
        markdown = (content or "").strip()
        if not markdown:
            return DraftStageResult(fallback, {})
        return DraftStageResult(markdown, _usage_dict(usage))
    except Exception:
        return DraftStageResult(fallback, {})


__all__ = ["DraftStageResult", "generate_summary_markdown"]
