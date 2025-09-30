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


def generate_summary_markdown(
    *,
    parse: TranscriptParse,
    outline: Dict[str, Any],
    timeline: List[Dict[str, Any]],
    entities: Dict[str, Any],
    intake: Dict[str, Any],
    context_snippet: Any,
    case_brief: Dict[str, Any],
    azure_client: Optional[AzureChatClient],
    temperature: float,
    max_tokens: int,
) -> DraftStageResult:
    if azure_client is None:
        raise RuntimeError("Azure client is required for summary stage")

    try:
        if isinstance(context_snippet, (list, tuple)):
            context_snippet = context_snippet[0] if context_snippet else ""
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
            "Case brief summary:\n"
            f"{json.dumps(case_brief, ensure_ascii=False, indent=2)}\n\n"
            "Transcript excerpts:\n"
            f"{context_snippet}\n"
        )
        content, usage = azure_client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max(1, max_tokens),
        )
        markdown = (content or "").strip()
        if not markdown:
            raise RuntimeError("Azure summary stage returned empty content")
        return DraftStageResult(markdown, _usage_dict(usage))
    except Exception as exc:
        raise RuntimeError(f"Azure summary stage failed: {exc}") from exc


__all__ = ["DraftStageResult", "generate_summary_markdown"]
