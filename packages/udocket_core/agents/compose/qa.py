from __future__ import annotations

# pyright: strict

import json
import logging
from typing import Mapping, Optional, Tuple

from ...utils.json import JSONObject, JSONValue, coerce_json_object, coerce_str

from .errors import ComposeStageError
from .llm_runtime import invoke_llm
from .state import ComposeState, LaneActionDirective, LaneQAResult
from ...llm import LLMSettings
from .settings import ComposeConfig

MAX_QA_PARSE_ATTEMPTS = 2


def run_lane_qa_review(
    *,
    state: ComposeState,
    lane: str,
    document: str,
    config: ComposeConfig,
    settings: LLMSettings,
    provider_credentials: Mapping[str, JSONObject],
    logger: logging.Logger,
    system_prompt: str,
) -> Tuple[LaneQAResult, dict[str, int], str, str]:
    """Execute QA for a single lane with resilient JSON parsing."""

    if state.context is None:
        raise ComposeStageError(f"compose.{lane}.qa_reviewer", "Compose context missing", lane=lane)

    payload = _lane_qa_payload(state, lane, document)
    last_error: Optional[str] = None
    stage_name = f"compose.{lane}.qa_reviewer"

    for attempt in range(1, MAX_QA_PARSE_ATTEMPTS + 1):
        user_prompt = json.dumps(payload, ensure_ascii=False)
        response, usage, provider, model = invoke_llm(
            stage=stage_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            provider_credentials=provider_credentials,
            config=config,
            settings=settings,
        )

        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as exc:
            last_error = f"QA reviewer returned malformed JSON: {exc}"
            logger.warning(
                f"{stage_name}.parse_error",
                extra={"attempt": attempt, "error": str(exc)},
            )
            payload["format_hint"] = "Return valid JSON only. Do not include commentary."
            continue

        try:
            result = _parse_lane_qa_payload(parsed, provider, model, lane)
        except ComposeStageError as exc:
            last_error = str(exc)
            logger.warning(
                f"{stage_name}.invalid_payload",
                extra={"attempt": attempt, "error": str(exc)},
            )
            payload["format_hint"] = (
                "Ensure keys: status, alerts, recommendations, staff_report, global_notes, action, reason, revision_brief."
            )
            continue

        return result, dict(usage), provider, model

    raise ComposeStageError(stage_name, last_error or "QA reviewer failed to return valid JSON", lane=lane)


def _lane_qa_payload(state: ComposeState, lane: str, document: str) -> JSONObject:
    context = state.context
    assert context is not None
    payload: JSONObject = {
        "lane": lane,
        "document": document,
        "compose_context": context.procedural,
        "claimable_atoms": list(context.claimable_atoms),
    }
    return coerce_json_object(payload)


def _coerce_str_list(value: JSONValue) -> list[str]:
    result: list[str] = []
    if isinstance(value, list):
        for item in value:
            text = coerce_str(item)
            if text:
                result.append(text)
    return result


def _parse_lane_qa_payload(
    payload: Mapping[str, JSONValue],
    provider: str,
    model: str,
    lane: str,
) -> LaneQAResult:
    status = coerce_str(payload.get("status")) or "unknown"
    alerts = _coerce_str_list(payload.get("alerts"))
    recommendations = _coerce_str_list(payload.get("recommendations"))
    staff_report = coerce_str(payload.get("staff_report")) or ""
    if not staff_report.strip():
        staff_report = "# Staff Report\n\nNo staff report returned."
    global_notes = coerce_str(payload.get("global_notes")) or ""
    action_value = coerce_str(payload.get("action")) or "none"
    normalized_action = action_value.strip().lower()
    allowed_actions = {"revise", "editor", "none"}
    if normalized_action not in allowed_actions:
        raise ComposeStageError(
            f"compose.{lane}.qa_reviewer",
            f"Unsupported action '{action_value}'",
            lane=lane,
            provider=provider,
            model=model,
        )
    revision_brief = (coerce_str(payload.get("revision_brief")) or "").strip()
    reason = (coerce_str(payload.get("reason")) or "").strip()
    if normalized_action != "none" and not reason:
        raise ComposeStageError(
            f"compose.{lane}.qa_reviewer",
            f"QA action '{normalized_action}' missing 'reason'",
            lane=lane,
            provider=provider,
            model=model,
        )
    directive = LaneActionDirective(
        action=normalized_action,
        revision_brief=revision_brief,
        reason=reason or None,
    )
    return LaneQAResult(
        status=status,
        alerts=alerts,
        recommendations=recommendations,
        staff_report=staff_report,
        provider=provider,
        action=directive,
        global_notes=global_notes,
    )


__all__ = ["run_lane_qa_review"]
