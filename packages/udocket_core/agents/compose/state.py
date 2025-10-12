from __future__ import annotations

# pyright: strict

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Sequence

from typing_extensions import Annotated

from ...utils.json import JSONObject, JSONValue, coerce_json_object, coerce_str

from ..common.factories import (
    int_usage_factory,
    float_usage_factory,
    json_object_factory,
    json_object_list_factory,
    stage_usage_factory,
    str_list_factory,
)
from .errors import ComposeStageError
from .llm_profiles import LaneConfig, LANE_CONFIGS


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


def _lane_qa_result_map_factory() -> dict[str, "LaneQAResult"]:
    return {}

def _merge_lane_qa_results(
    existing: Optional[dict[str, "LaneQAResult"]],
    update: Optional[dict[str, Optional["LaneQAResult"]]],
) -> dict[str, "LaneQAResult"]:
    merged: dict[str, LaneQAResult] = {}
    if existing:
        merged = {lane: result for lane, result in existing.items()}
    if update:
        for lane, result in update.items():
            if result is None:
                merged.pop(lane, None)
            else:
                merged[lane] = result
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
class LaneQAResult:
    status: str
    alerts: list[str]
    recommendations: list[str]
    staff_report: str
    provider: str
    action: LaneActionDirective
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
    qa_lane_results: Annotated[dict[str, LaneQAResult], _merge_lane_qa_results] = field(default_factory=_lane_qa_result_map_factory)
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


def lane_qa_result_to_json(result: LaneQAResult) -> JSONObject:
    return {
        "status": result.status,
        "alerts": list(result.alerts),
        "recommendations": list(result.recommendations),
        "staff_report": result.staff_report,
        "provider": result.provider,
        "global_notes": result.global_notes,
        "action": lane_action_to_json(result.action),
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


def _json_str_list(value: JSONValue) -> list[str]:
    results: list[str] = []
    if isinstance(value, (list, tuple)):
        for item in value:
            text = coerce_str(item)
            if text:
                results.append(text)
    return results


def _json_object_list(value: JSONValue) -> list[JSONObject]:
    results: list[JSONObject] = []
    if isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, Mapping):
                results.append(coerce_json_object(item))
    return results


def _int_from_json(value: JSONValue) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0


def _float_from_json(value: JSONValue) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _guard_report_from_json(value: JSONValue) -> GuardReport | None:
    if not isinstance(value, Mapping):
        return None
    errors = _json_str_list(value.get("errors"))
    warnings = _json_str_list(value.get("warnings"))
    checks_raw = value.get("checks")
    checks = coerce_json_object(checks_raw) if isinstance(checks_raw, Mapping) else {}
    return GuardReport(
        ok=bool(value.get("ok")),
        errors=errors,
        warnings=warnings,
        checks=checks,
    )


def _lane_action_from_json(value: JSONValue) -> LaneActionDirective:
    if not isinstance(value, Mapping):
        return LaneActionDirective(action="none")
    action = coerce_str(value.get("action")) or "none"
    directive = LaneActionDirective(
        action=action,
        revision_brief=coerce_str(value.get("revision_brief")) or None,
        reason=coerce_str(value.get("reason")) or None,
    )
    original = coerce_str(value.get("original_action"))
    if original:
        directive.original_action = original
    return directive


def _lane_attempt_from_json(value: JSONValue) -> LaneAttempt:
    if not isinstance(value, Mapping):
        raise ComposeStageError("compose.resume", "Lane attempt payload malformed")
    structure = _guard_report_from_json(value.get("structure"))
    compliance = _guard_report_from_json(value.get("compliance"))
    factuality = _guard_report_from_json(value.get("factuality"))
    structure_report = structure or GuardReport(ok=False, errors=[], warnings=[], checks={})
    compliance_report = compliance or GuardReport(ok=False, errors=[], warnings=[], checks={})
    factuality_report = factuality or GuardReport(ok=False, errors=[], warnings=[], checks={})
    return LaneAttempt(
        attempt_number=_int_from_json(value.get("attempt")),
        source=coerce_str(value.get("source")) or "draft",
        document=coerce_str(value.get("document")) or "",
        structure=structure_report,
        compliance=compliance_report,
        factuality=factuality_report,
    )


def _lane_outcome_from_json(value: JSONValue) -> LaneOutcome:
    if not isinstance(value, Mapping):
        raise ComposeStageError("compose.resume", "Lane outcome payload malformed")
    structure_report = _guard_report_from_json(value.get("structure_report"))
    compliance_report = _guard_report_from_json(value.get("compliance_report"))
    factuality_report = _guard_report_from_json(value.get("factuality_report"))
    history_raw = value.get("history")
    history: list[LaneAttempt] = []
    if isinstance(history_raw, (list, tuple)):
        for item in history_raw:
            history.append(_lane_attempt_from_json(item))
    stage_usage_raw = value.get("stage_usage")
    stage_usage: dict[str, dict[str, int]] = {}
    if isinstance(stage_usage_raw, Mapping):
        for stage, metrics in stage_usage_raw.items():
            if isinstance(metrics, Mapping):
                stage_metrics: dict[str, int] = {}
                for metric_key, metric_value in metrics.items():
                    stage_metrics[str(metric_key)] = _int_from_json(metric_value)
                stage_usage[str(stage)] = stage_metrics
    token_usage_raw = value.get("token_usage")
    token_usage: dict[str, int] = {}
    if isinstance(token_usage_raw, Mapping):
        for key, token_value in token_usage_raw.items():
            token_usage[str(key)] = _int_from_json(token_value)
    stage_durations_raw = value.get("stage_durations")
    stage_durations: dict[str, float] = {}
    if isinstance(stage_durations_raw, Mapping):
        for stage, duration in stage_durations_raw.items():
            stage_durations[str(stage)] = _float_from_json(duration)
    providers = _json_str_list(value.get("providers"))
    models = _json_str_list(value.get("models"))
    return LaneOutcome(
        document=coerce_str(value.get("document")) or "",
        structure_report=structure_report or GuardReport(ok=False, errors=[], warnings=[], checks={}),
        compliance_report=compliance_report or GuardReport(ok=False, errors=[], warnings=[], checks={}),
        factuality_report=factuality_report or GuardReport(ok=False, errors=[], warnings=[], checks={}),
        attempts=_int_from_json(value.get("attempts")),
        history=history,
        stage_usage=stage_usage,
        token_usage=token_usage,
        providers=providers,
        models=models,
        stage_durations=stage_durations,
    )


def _lane_runtime_state_from_json(value: JSONValue) -> LaneRuntimeState:
    if not isinstance(value, Mapping):
        raise ComposeStageError("compose.resume", "Lane runtime payload malformed")
    lane_name = coerce_str(value.get("lane")) or "client"
    config_payload = value.get("config")
    config_lane_value: JSONValue | None = None
    if isinstance(config_payload, Mapping):
        config_lane_value = config_payload.get("lane")
    config_lane = coerce_str(config_lane_value) or lane_name
    lane_config = LANE_CONFIGS.get(config_lane)
    if lane_config is None:
        raise ComposeStageError("compose.resume", f"Unknown lane configuration '{config_lane}'")
    history_raw = value.get("history")
    history: list[LaneAttempt] = []
    if isinstance(history_raw, (list, tuple)):
        for item in history_raw:
            history.append(_lane_attempt_from_json(item))
    stage_usage_raw = value.get("stage_usage")
    stage_usage: dict[str, dict[str, int]] = {}
    if isinstance(stage_usage_raw, Mapping):
        for stage, metrics in stage_usage_raw.items():
            if isinstance(metrics, Mapping):
                metric_bucket: dict[str, int] = {}
                for metric_key, metric_value in metrics.items():
                    metric_bucket[str(metric_key)] = _int_from_json(metric_value)
                stage_usage[str(stage)] = metric_bucket
    token_usage_raw = value.get("token_usage")
    token_usage: dict[str, int] = {}
    if isinstance(token_usage_raw, Mapping):
        for key, token_value in token_usage_raw.items():
            token_usage[str(key)] = _int_from_json(token_value)
    stage_durations_raw = value.get("stage_durations")
    stage_durations: dict[str, float] = {}
    if isinstance(stage_durations_raw, Mapping):
        for stage, duration in stage_durations_raw.items():
            stage_durations[str(stage)] = _float_from_json(duration)
    structure_report = _guard_report_from_json(value.get("structure_report"))
    compliance_report = _guard_report_from_json(value.get("compliance_report"))
    factuality_report = _guard_report_from_json(value.get("factuality_report"))
    providers = _json_str_list(value.get("providers"))
    models = _json_str_list(value.get("models"))
    return LaneRuntimeState(
        lane=lane_name,
        config=lane_config,
        max_attempts=_int_from_json(value.get("max_attempts")),
        attempts=_int_from_json(value.get("attempts")),
        current_source=coerce_str(value.get("current_source")) or "draft",
        revision_brief=coerce_str(value.get("revision_brief")) or None,
        last_document_hash=coerce_str(value.get("last_document_hash")) or None,
        document=coerce_str(value.get("document")) or None,
        structure_report=structure_report,
        compliance_report=compliance_report,
        factuality_report=factuality_report,
        history=history,
        stage_usage=stage_usage,
        token_usage=token_usage,
        providers=providers,
        models=models,
        editor_attempted=bool(value.get("editor_attempted")),
        stage_durations=stage_durations,
    )


def _qa_result_from_json(value: JSONValue) -> QAReviewerResult | None:
    if not isinstance(value, Mapping):
        return None
    lane_actions_raw = value.get("lane_actions")
    lane_actions: dict[str, LaneActionDirective] = {}
    if isinstance(lane_actions_raw, Mapping):
        for lane, directive in lane_actions_raw.items():
            lane_actions[str(lane)] = _lane_action_from_json(directive)
    return QAReviewerResult(
        status=coerce_str(value.get("status")) or "unknown",
        alerts=_json_str_list(value.get("alerts")),
        recommendations=_json_str_list(value.get("recommendations")),
        staff_report=coerce_str(value.get("staff_report")) or "",
        provider=coerce_str(value.get("provider")) or "",
        lane_actions=lane_actions,
        global_notes=coerce_str(value.get("global_notes")) or "",
    )


def _lane_qa_result_from_json(value: JSONValue) -> LaneQAResult:
    if not isinstance(value, Mapping):
        raise ComposeStageError("compose.resume", "Lane QA result payload malformed")
    return LaneQAResult(
        status=coerce_str(value.get("status")) or "unknown",
        alerts=_json_str_list(value.get("alerts")),
        recommendations=_json_str_list(value.get("recommendations")),
        staff_report=coerce_str(value.get("staff_report")) or "",
        provider=coerce_str(value.get("provider")) or "",
        action=_lane_action_from_json(value.get("action")),
        global_notes=coerce_str(value.get("global_notes")) or "",
    )


def compose_context_from_json(value: Optional[JSONValue]) -> Optional[ComposeContext]:
    if not isinstance(value, Mapping):
        return None
    return ComposeContext(
        parties=_json_object_list(value.get("parties")),
        issues=_json_object_list(value.get("issues")),
        facts=_json_object_list(value.get("facts")),
        events=_json_object_list(value.get("events")),
        deadlines=_json_object_list(value.get("deadlines")),
        orders=_json_object_list(value.get("orders")),
        exhibits=_json_object_list(value.get("exhibits")),
        procedural=coerce_json_object(value.get("procedural")) if isinstance(value.get("procedural"), Mapping) else {},
        claimable_atoms=_json_str_list(value.get("claimable_atoms")),
    )


def compose_inputs_from_json(value: JSONValue) -> ComposeInputs:
    if not isinstance(value, Mapping):
        raise ComposeStageError("compose.resume", "Compose inputs payload malformed")
    timeline_seeds = _json_object_list(value.get("timeline_seeds"))
    return ComposeInputs(
        summary_markdown=coerce_str(value.get("summary_markdown")) or "",
        summary_data=coerce_json_object(value.get("summary_data")) if isinstance(value.get("summary_data"), Mapping) else {},
        timeline_seeds=timeline_seeds,
        entity_hints=coerce_json_object(value.get("entity_hints")) if isinstance(value.get("entity_hints"), Mapping) else {},
        intake=coerce_json_object(value.get("intake")) if isinstance(value.get("intake"), Mapping) else {},
        case_metadata=coerce_json_object(value.get("case_metadata")) if isinstance(value.get("case_metadata"), Mapping) else {},
    )


def compose_state_from_json(payload: Mapping[str, JSONValue]) -> ComposeState:
    inputs = compose_inputs_from_json(payload.get("inputs"))
    client_state = _lane_runtime_state_from_json(payload.get("client"))
    lawyer_state = _lane_runtime_state_from_json(payload.get("lawyer"))
    context = compose_context_from_json(payload.get("context"))
    lanes_raw = payload.get("lanes")
    lanes: dict[str, LaneOutcome] = {}
    if isinstance(lanes_raw, Mapping):
        for lane, data in lanes_raw.items():
            lanes[str(lane)] = _lane_outcome_from_json(data)
    qa_result = _qa_result_from_json(payload.get("qa"))
    qa_lane_results_raw = payload.get("qa_lane_results")
    qa_lane_results: dict[str, LaneQAResult] = {}
    if isinstance(qa_lane_results_raw, Mapping):
        for lane, data in qa_lane_results_raw.items():
            qa_lane_results[str(lane)] = _lane_qa_result_from_json(data)
    stage_usage_raw = payload.get("stage_usage")
    stage_usage: dict[str, dict[str, int]] = {}
    if isinstance(stage_usage_raw, Mapping):
        for stage, metrics in stage_usage_raw.items():
            if isinstance(metrics, Mapping):
                metric_bucket: dict[str, int] = {}
                for metric_key, metric_value in metrics.items():
                    metric_bucket[str(metric_key)] = _int_from_json(metric_value)
                stage_usage[str(stage)] = metric_bucket
    stage_durations_raw = payload.get("stage_durations")
    stage_durations: dict[str, float] = {}
    if isinstance(stage_durations_raw, Mapping):
        for stage, duration in stage_durations_raw.items():
            stage_durations[str(stage)] = _float_from_json(duration)
    qa_iterations = _int_from_json(payload.get("qa_iterations"))
    return ComposeState(
        inputs=inputs,
        client=client_state,
        lawyer=lawyer_state,
        context=context,
        lanes=lanes,
        qa=qa_result,
        qa_lane_results=qa_lane_results,
        stage_usage=stage_usage,
        qa_iterations=qa_iterations,
        stage_durations=stage_durations,
    )


def serialize_compose_state(state: ComposeState) -> JSONObject:
    return {
        "inputs": compose_inputs_to_json(state.inputs),
        "client": lane_runtime_state_to_json(state.client),
        "lawyer": lane_runtime_state_to_json(state.lawyer),
        "context": compose_context_to_json(state.context),
        "lanes": {lane: lane_outcome_to_json(outcome) for lane, outcome in state.lanes.items()},
        "qa": qa_result_to_json(state.qa) if state.qa else None,
        "qa_lane_results": {lane: lane_qa_result_to_json(result) for lane, result in state.qa_lane_results.items()},
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
    "LaneQAResult",
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
    "compose_inputs_from_json",
    "compose_context_from_json",
    "serialize_compose_state",
    "compose_state_from_json",
]
