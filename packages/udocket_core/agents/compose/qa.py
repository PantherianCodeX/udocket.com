from __future__ import annotations

# pyright: strict

import json
import logging
from typing import Mapping, Optional, Tuple

from packages.udocket_core.json_utils import JSONObject, JSONValue, coerce_json_object, coerce_str

from .errors import ComposeStageError
from .llm_runtime import invoke_llm
from .state import ComposeState, LaneActionDirective, QAReviewerResult
from ...llm import LLMSettings
from .settings import ComposeConfig

MAX_QA_PARSE_ATTEMPTS = 2


def run_qa_review(
    *,
    state: ComposeState,
    config: ComposeConfig,
    settings: LLMSettings,
    provider_credentials: Mapping[str, JSONObject],
    logger: logging.Logger,
    system_prompt: str,
) -> Tuple[QAReviewerResult, dict[str, int], str, str]:
    """Call the QA reviewer LLM with resilient JSON parsing."""

    if state.context is None:
        raise ComposeStageError("compose.qa_reviewer", "Compose context missing")
    if "client" not in state.lanes or "lawyer" not in state.lanes:
        raise ComposeStageError("compose.qa_reviewer", "QA reviewer invoked before lane outcomes ready")

    payload = _qa_payload(state)
    last_error: Optional[str] = None

    for attempt in range(1, MAX_QA_PARSE_ATTEMPTS + 1):
        user_prompt = json.dumps(payload, ensure_ascii=False)
        response, usage, provider, model = invoke_llm(
            stage="compose.qa_reviewer",
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
                "compose.qa_reviewer.parse_error",
                extra={"attempt": attempt, "error": str(exc)},
            )
            payload["format_hint"] = "Return valid JSON only. Do not include commentary."
            continue

        try:
            result = _parse_qa_payload(parsed, provider, model)
        except ComposeStageError as exc:
            last_error = str(exc)
            logger.warning(
                "compose.qa_reviewer.invalid_payload",
                extra={"attempt": attempt, "error": str(exc)},
            )
            payload["format_hint"] = (
                "Ensure keys: status, alerts, recommendations, staff_report, global_notes, lane_actions "
                "with client/lawyer actions."
            )
            continue

        return result, dict(usage), provider, model

    raise ComposeStageError("compose.qa_reviewer", last_error or "QA reviewer failed to return valid JSON")


def _qa_payload(state: ComposeState) -> JSONObject:
    context = state.context
    assert context is not None
    return coerce_json_object(
        {
            "compose_context": context.procedural,
            "claimable_atoms": context.claimable_atoms,
            "client_brief": state.lanes["client"].document,
            "lawyer_brief": state.lanes["lawyer"].document,
        }
    )


def _parse_qa_payload(
    payload: Mapping[str, JSONValue],
    provider: str,
    model: str,
) -> QAReviewerResult:
    status = coerce_str(payload.get("status")) or "unknown"
    alerts = _coerce_str_list(payload.get("alerts"))
    recommendations = _coerce_str_list(payload.get("recommendations"))
    staff_report = coerce_str(payload.get("staff_report")) or ""
    if not staff_report.strip():
        staff_report = "# Staff Report\n\nNo staff report returned."
    global_notes = coerce_str(payload.get("global_notes")) or ""
    lane_actions_payload = payload.get("lane_actions")
    lane_actions: dict[str, LaneActionDirective] = {}
    if isinstance(lane_actions_payload, Mapping):
        lane_actions = _parse_lane_actions(lane_actions_payload, provider, model)
    else:
        raise ComposeStageError(
            "compose.qa_reviewer",
            "QA reviewer payload missing lane_actions",
            provider=provider,
            model=model,
        )
    return QAReviewerResult(
        status=status,
        alerts=alerts,
        recommendations=recommendations,
        staff_report=staff_report,
        provider=provider,
        lane_actions=lane_actions,
        global_notes=global_notes,
    )


def _coerce_str_list(value: JSONValue) -> list[str]:
    result: list[str] = []
    if isinstance(value, list):
        for item in value:
            text = coerce_str(item)
            if text:
                result.append(text)
    return result


def _parse_lane_actions(
    payload: Mapping[str, JSONValue],
    provider: str,
    model: str,
) -> dict[str, LaneActionDirective]:
    allowed_actions = {"revise", "editor", "none"}
    lane_actions: dict[str, LaneActionDirective] = {}
    for lane in ("client", "lawyer"):
        directive_raw = payload.get(lane)
        directive_obj = coerce_json_object(directive_raw) if isinstance(directive_raw, Mapping) else {}
        action_value = coerce_str(directive_obj.get("action")) or "none"
        normalized_action = action_value.strip().lower()
        if normalized_action not in allowed_actions:
            raise ComposeStageError(
                "compose.qa_reviewer",
                f"Unsupported action '{action_value}' for lane '{lane}'",
                lane=lane,
                provider=provider,
                model=model,
            )
        revision_brief = (coerce_str(directive_obj.get("revision_brief")) or "").strip()
        reason = (coerce_str(directive_obj.get("reason")) or "").strip()
        if normalized_action != "none" and not reason:
            raise ComposeStageError(
                "compose.qa_reviewer",
                f"QA action '{normalized_action}' for lane '{lane}' missing 'reason'",
                lane=lane,
                provider=provider,
                model=model,
            )
        lane_actions[lane] = LaneActionDirective(
            action=normalized_action,
            revision_brief=revision_brief,
            reason=reason or None,
        )
    return lane_actions


__all__ = ["run_qa_review"]
