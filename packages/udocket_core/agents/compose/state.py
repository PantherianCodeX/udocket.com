from __future__ import annotations

# pyright: strict

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Sequence

from typing_extensions import Annotated

from packages.udocket_core.json_utils import JSONObject

from ..common.factories import (
    int_usage_factory,
    float_usage_factory,
    json_object_factory,
    json_object_list_factory,
    stage_usage_factory,
    str_list_factory,
)
from .errors import ComposeStageError
from .llm_profiles import LaneConfig


def _merge_usage(target: dict[str, dict[str, int]], stage: str, usage: Mapping[str, int]) -> None:
    stage_bucket = target.setdefault(stage, {})
    for key, value in usage.items():
        stage_bucket[key] = stage_bucket.get(key, 0) + int(value)


def _merge_stage_usage(
    existing: Optional[dict[str, dict[str, int]]],
    update: Optional[dict[str, dict[str, int]]],
) -> dict[str, dict[str, int]]:
    if not existing and not update:
        return {}
    merged: dict[str, dict[str, int]] = {
        stage: dict(values) for stage, values in (existing or {}).items()
    }
    for stage, usage in (update or {}).items():
        bucket = merged.setdefault(stage, {})
        for key, value in usage.items():
            bucket[key] = bucket.get(key, 0) + int(value)
    return merged


def _merge_stage_durations(
    existing: Optional[dict[str, float]],
    update: Optional[dict[str, float]],
) -> dict[str, float]:
    merged: dict[str, float] = {}
    if existing:
        merged = {stage: float(value) for stage, value in existing.items()}
    if update:
        for stage, duration in update.items():
            merged[stage] = merged.get(stage, 0.0) + float(duration)
    return merged


def _lane_attempt_list_factory() -> list["LaneAttempt"]:
    return []


def _lane_action_map_factory() -> dict[str, "LaneActionDirective"]:
    return {}


def _lane_outcome_map_factory() -> dict[str, "LaneOutcome"]:
    return {}


def _merge_lane_outcomes(
    existing: Optional[dict[str, "LaneOutcome"]],
    update: Optional[dict[str, Optional["LaneOutcome"]]],
) -> dict[str, "LaneOutcome"]:
    merged: dict[str, LaneOutcome] = {}
    if existing:
        merged = {lane: outcome for lane, outcome in existing.items()}
    if update:
        for lane, outcome in update.items():
            if outcome is None:
                merged.pop(lane, None)
            else:
                merged[lane] = outcome
    return merged


def _latest_lane_state(
    existing: Optional["LaneRuntimeState"],
    update: Optional["LaneRuntimeState"],
) -> "LaneRuntimeState":
    if update is not None:
        return update
    if existing is not None:
        return existing
    raise ComposeStageError("compose.lane_state", "Lane state missing for reducer")


@dataclass(slots=True)
class ComposeInputs:
    summary_markdown: str
    summary_data: JSONObject
    timeline_seeds: list[JSONObject]
    entity_hints: JSONObject
    intake: JSONObject
    case_metadata: JSONObject


@dataclass(slots=True)
class ComposeContext:
    parties: list[JSONObject] = field(default_factory=json_object_list_factory)
    issues: list[JSONObject] = field(default_factory=json_object_list_factory)
    facts: list[JSONObject] = field(default_factory=json_object_list_factory)
    events: list[JSONObject] = field(default_factory=json_object_list_factory)
    deadlines: list[JSONObject] = field(default_factory=json_object_list_factory)
    orders: list[JSONObject] = field(default_factory=json_object_list_factory)
    exhibits: list[JSONObject] = field(default_factory=json_object_list_factory)
    procedural: JSONObject = field(default_factory=json_object_factory)
    claimable_atoms: list[str] = field(default_factory=str_list_factory)


@dataclass(slots=True)
class GuardReport:
    ok: bool
    errors: list[str] = field(default_factory=str_list_factory)
    warnings: list[str] = field(default_factory=str_list_factory)
    checks: JSONObject = field(default_factory=json_object_factory)


@dataclass(slots=True)
class LaneActionDirective:
    action: str
    revision_brief: Optional[str] = None
    reason: Optional[str] = None
    original_action: str = field(init=False)

    def __post_init__(self) -> None:
        self.original_action = self.action


@dataclass(slots=True)
class LaneAttempt:
    attempt_number: int
    source: str
    document: str
    structure: GuardReport
    compliance: GuardReport
    factuality: GuardReport


@dataclass(slots=True)
class LaneOutcome:
    document: str
    structure_report: GuardReport
    compliance_report: GuardReport
    factuality_report: GuardReport
    attempts: int
    history: list[LaneAttempt]
    stage_usage: dict[str, dict[str, int]]
    token_usage: dict[str, int]
    providers: list[str]
    models: list[str]
    stage_durations: dict[str, float]


@dataclass(slots=True)
class LaneRuntimeState:
    lane: str
    config: LaneConfig
    max_attempts: int
    attempts: int = 0
    current_source: str = "draft"
    revision_brief: Optional[str] = None
    last_document_hash: Optional[str] = None
    document: Optional[str] = None
    structure_report: Optional[GuardReport] = None
    compliance_report: Optional[GuardReport] = None
    factuality_report: Optional[GuardReport] = None
    history: list[LaneAttempt] = field(default_factory=_lane_attempt_list_factory)
    stage_usage: dict[str, dict[str, int]] = field(default_factory=stage_usage_factory)
    token_usage: dict[str, int] = field(default_factory=int_usage_factory)
    providers: list[str] = field(default_factory=str_list_factory)
    models: list[str] = field(default_factory=str_list_factory)
    editor_attempted: bool = False
    stage_durations: dict[str, float] = field(default_factory=float_usage_factory)

    def record_usage(self, stage: str, usage: Mapping[str, int]) -> None:
        _merge_usage(self.stage_usage, stage, usage)
        for key, value in usage.items():
            self.token_usage[key] = self.token_usage.get(key, 0) + int(value)

    def record_duration(self, stage: str, duration: float) -> None:
        if duration <= 0:
            return
        self.stage_durations[stage] = self.stage_durations.get(stage, 0.0) + float(duration)

    def to_outcome(self) -> "LaneOutcome":
        if (
            self.document is None
            or self.structure_report is None
            or self.compliance_report is None
            or self.factuality_report is None
        ):
            raise ComposeStageError(
                f"compose.{self.lane}", "Lane outcome requested before completion"
            )
        return LaneOutcome(
            document=self.document,
            structure_report=clone_guard_report(self.structure_report),
            compliance_report=clone_guard_report(self.compliance_report),
            factuality_report=clone_guard_report(self.factuality_report),
            attempts=self.attempts,
            history=list(self.history),
            stage_usage={stage: dict(values) for stage, values in self.stage_usage.items()},
            token_usage=dict(self.token_usage),
            providers=list(self.providers),
            models=list(self.models),
            stage_durations={stage: float(value) for stage, value in self.stage_durations.items()},
        )


@dataclass(slots=True)
class QAReviewerResult:
    status: str
    alerts: list[str]
    recommendations: list[str]
    staff_report: str
    provider: str
    lane_actions: dict[str, LaneActionDirective] = field(default_factory=_lane_action_map_factory)
    global_notes: str = ""


@dataclass(slots=True)
class ComposeArtifacts:
    client_markdown: Optional[Path] = None
    lawyer_markdown: Optional[Path] = None
    client_docx: Optional[Path] = None
    lawyer_docx: Optional[Path] = None
    bundle_path: Optional[Path] = None
    qa_report: Optional[Path] = None
    staff_report: Optional[Path] = None
    timeline_file: Optional[Path] = None
    graph_file: Optional[Path] = None
    entities_file: Optional[Path] = None
    timeline_summary: Optional[Path] = None
    entity_brief: Optional[Path] = None
    graph_visual_json: Optional[Path] = None
    graph_html: Optional[Path] = None
    graph_image: Optional[Path] = None


@dataclass(slots=True)
class ComposeResult:
    status: str
    artifacts: ComposeArtifacts
    meta_json: Path
    audit_jsonl: Path
    provider_chain: list[str]
    stage_usage: dict[str, dict[str, int]]
    stage_durations: dict[str, float]


@dataclass(slots=True)
class ComposeState:
    inputs: ComposeInputs
    client: Annotated[LaneRuntimeState, _latest_lane_state]
    lawyer: Annotated[LaneRuntimeState, _latest_lane_state]
    context: Optional[ComposeContext] = None
    lanes: Annotated[dict[str, LaneOutcome], _merge_lane_outcomes] = field(default_factory=_lane_outcome_map_factory)
    qa: Optional[QAReviewerResult] = None
    stage_usage: Annotated[dict[str, dict[str, int]], _merge_stage_usage] = field(default_factory=stage_usage_factory)
    qa_iterations: int = 0
    stage_durations: Annotated[dict[str, float], _merge_stage_durations] = field(default_factory=float_usage_factory)


def clone_guard_report(report: GuardReport) -> GuardReport:
    return GuardReport(
        ok=report.ok,
        errors=list(report.errors),
        warnings=list(report.warnings),
        checks=dict(report.checks),
    )


def lane_history_payload(history: Sequence[LaneAttempt]) -> list[JSONObject]:
    payload: list[JSONObject] = []
    for attempt in history:
        payload.append(
            {
                "attempt": attempt.attempt_number,
                "source": attempt.source,
                "structure": guard_report_to_json(attempt.structure),
                "compliance": guard_report_to_json(attempt.compliance),
                "factuality": guard_report_to_json(attempt.factuality),
            }
        )
    return payload


def guard_report_to_json(report: GuardReport) -> JSONObject:
    return {
        "ok": report.ok,
        "errors": list(report.errors),
        "warnings": list(report.warnings),
        "checks": dict(report.checks),
    }


def lane_attempt_to_json(attempt: LaneAttempt) -> JSONObject:
    return {
        "attempt": attempt.attempt_number,
        "source": attempt.source,
        "document": attempt.document,
        "structure": guard_report_to_json(attempt.structure),
        "compliance": guard_report_to_json(attempt.compliance),
        "factuality": guard_report_to_json(attempt.factuality),
    }


def lane_outcome_to_json(outcome: LaneOutcome) -> JSONObject:
    return {
        "document": outcome.document,
        "structure_report": guard_report_to_json(outcome.structure_report),
        "compliance_report": guard_report_to_json(outcome.compliance_report),
        "factuality_report": guard_report_to_json(outcome.factuality_report),
        "attempts": outcome.attempts,
        "history": [lane_attempt_to_json(attempt) for attempt in outcome.history],
        "stage_usage": {stage: dict(values) for stage, values in outcome.stage_usage.items()},
        "token_usage": dict(outcome.token_usage),
        "providers": list(outcome.providers),
        "models": list(outcome.models),
        "stage_durations": {stage: float(value) for stage, value in outcome.stage_durations.items()},
    }


def lane_runtime_state_to_json(runtime: LaneRuntimeState) -> JSONObject:
    return {
        "lane": runtime.lane,
        "config": {"lane": runtime.config.lane},
        "max_attempts": runtime.max_attempts,
        "attempts": runtime.attempts,
        "current_source": runtime.current_source,
        "revision_brief": runtime.revision_brief,
        "last_document_hash": runtime.last_document_hash,
        "document": runtime.document,
        "structure_report": guard_report_to_json(runtime.structure_report) if runtime.structure_report else None,
        "compliance_report": guard_report_to_json(runtime.compliance_report) if runtime.compliance_report else None,
        "factuality_report": guard_report_to_json(runtime.factuality_report) if runtime.factuality_report else None,
        "history": [lane_attempt_to_json(attempt) for attempt in runtime.history],
        "stage_usage": {stage: dict(values) for stage, values in runtime.stage_usage.items()},
        "token_usage": dict(runtime.token_usage),
        "providers": list(runtime.providers),
        "models": list(runtime.models),
        "editor_attempted": runtime.editor_attempted,
        "stage_durations": {stage: float(value) for stage, value in runtime.stage_durations.items()},
    }


def lane_action_to_json(action: LaneActionDirective) -> JSONObject:
    return {
        "action": action.action,
        "original_action": action.original_action,
        "revision_brief": action.revision_brief,
        "reason": action.reason,
    }


def qa_result_to_json(result: QAReviewerResult) -> JSONObject:
    return {
        "status": result.status,
        "alerts": list(result.alerts),
        "recommendations": list(result.recommendations),
        "staff_report": result.staff_report,
        "provider": result.provider,
        "global_notes": result.global_notes,
        "lane_actions": {lane: lane_action_to_json(action) for lane, action in result.lane_actions.items()},
    }


def compose_inputs_to_json(inputs: ComposeInputs) -> JSONObject:
    return {
        "summary_markdown": inputs.summary_markdown,
        "summary_data": dict(inputs.summary_data),
        "timeline_seeds": [dict(seed) for seed in inputs.timeline_seeds],
        "entity_hints": dict(inputs.entity_hints),
        "intake": dict(inputs.intake),
        "case_metadata": dict(inputs.case_metadata),
    }


def compose_context_to_json(context: Optional[ComposeContext]) -> Optional[JSONObject]:
    if context is None:
        return None
    return {
        "parties": [dict(party) for party in context.parties],
        "issues": [dict(issue) for issue in context.issues],
        "facts": [dict(fact) for fact in context.facts],
        "events": [dict(event) for event in context.events],
        "deadlines": [dict(deadline) for deadline in context.deadlines],
        "orders": [dict(order) for order in context.orders],
        "exhibits": [dict(exhibit) for exhibit in context.exhibits],
        "procedural": dict(context.procedural),
        "claimable_atoms": list(context.claimable_atoms),
    }


def serialize_compose_state(state: ComposeState) -> JSONObject:
    return {
        "inputs": compose_inputs_to_json(state.inputs),
        "client": lane_runtime_state_to_json(state.client),
        "lawyer": lane_runtime_state_to_json(state.lawyer),
        "context": compose_context_to_json(state.context),
        "lanes": {lane: lane_outcome_to_json(outcome) for lane, outcome in state.lanes.items()},
        "qa": qa_result_to_json(state.qa) if state.qa else None,
        "stage_usage": {stage: dict(values) for stage, values in state.stage_usage.items()},
        "qa_iterations": state.qa_iterations,
        "stage_durations": {stage: float(value) for stage, value in state.stage_durations.items()},
    }


__all__ = [
    "ComposeArtifacts",
    "ComposeContext",
    "ComposeInputs",
    "ComposeResult",
    "ComposeState",
    "GuardReport",
    "LaneActionDirective",
    "LaneAttempt",
    "LaneOutcome",
    "LaneRuntimeState",
    "QAReviewerResult",
    "clone_guard_report",
    "lane_history_payload",
    "guard_report_to_json",
    "lane_attempt_to_json",
    "lane_outcome_to_json",
    "lane_runtime_state_to_json",
    "lane_action_to_json",
    "qa_result_to_json",
    "compose_inputs_to_json",
    "compose_context_to_json",
    "serialize_compose_state",
]
