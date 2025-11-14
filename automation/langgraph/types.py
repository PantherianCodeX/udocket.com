# pyright: strict
"""Typed LangGraph state models plus adapters for LangGraph-compatible nodes."""

from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

from packages.ai.api import EntityHint, TimelineEvent
from packages.ai.types import CaseID, JobID, OrganizationID, ProviderCallMetrics
from packages.common.agents import StageKey
from packages.common.json_utils import JSONObject, coerce_json_object

if TYPE_CHECKING:
    from packages.core.agents.langgraph_orchestrator import AnalyzeNodeImpl, ComposeNodeImpl

StateMapping = MutableMapping[str, object]


@dataclass(slots=True, frozen=True)
class RunMetadata:
    """Case/job metadata shared across Analyze and Compose pipelines."""

    case_id: CaseID
    job_id: JobID
    org_id: OrganizationID | None = None
    case_dir: Path | None = None
    settings_snapshot_sha: str | None = None


@dataclass(slots=True, frozen=True)
class ArtifactRef:
    """Reference to a persisted artifact."""

    kind: str
    path: Path
    checksum: str | None = None


@dataclass(slots=True, frozen=True)
class OpsRecord:
    """Structured ops/audit payload recorded per run."""

    name: str
    payload: JSONObject
    stage_key: StageKey | None = None


@dataclass(slots=True, frozen=True)
class AnalyzeGraphState:
    """Typed state exchanged between Analyze LangGraph nodes."""

    metadata: RunMetadata
    transcript_path: Path | None = None
    transcript_text: str | None = None
    outline: JSONObject | None = None
    timeline_events: tuple[TimelineEvent, ...] = field(default_factory=tuple)
    entity_hints: tuple[EntityHint, ...] = field(default_factory=tuple)
    summary_markdown: str | None = None
    summary_json: JSONObject | None = None
    lane_payloads: dict[StageKey, JSONObject] = field(default_factory=dict)
    metrics: dict[StageKey, ProviderCallMetrics] = field(default_factory=dict)
    artifacts: tuple[ArtifactRef, ...] = field(default_factory=tuple)
    ops_records: tuple[OpsRecord, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class ComposeGraphState:
    """Typed state exchanged between Compose LangGraph nodes."""

    metadata: RunMetadata
    summary_json: JSONObject | None = None
    client_markdown: str | None = None
    lawyer_markdown: str | None = None
    qa_report: JSONObject | None = None
    lane_payloads: dict[StageKey, JSONObject] = field(default_factory=dict)
    metrics: dict[StageKey, ProviderCallMetrics] = field(default_factory=dict)
    artifacts: tuple[ArtifactRef, ...] = field(default_factory=tuple)
    ops_records: tuple[OpsRecord, ...] = field(default_factory=tuple)


_ANALYZE_METHODS: tuple[str, ...] = (
    "input_discovery",
    "parse_transcript",
    "context_builder",
    "extract_outline",
    "build_timeline_seeds",
    "build_entity_hints",
    "draft_markdown",
    "qa_and_finalize",
    "qa_join",
    "write_ops_and_artifacts",
)

_COMPOSE_METHODS: tuple[str, ...] = (
    "context_builder",
    "client_lane_draft",
    "client_lane_qa",
    "client_lane_editor",
    "client_lane_revise",
    "lawyer_lane_draft",
    "lawyer_lane_qa",
    "lawyer_lane_editor",
    "lawyer_lane_revise",
    "qa_join",
    "write_release_artifacts",
)


class TypedAnalyzeNodeImpl(Protocol):
    """Protocol for Analyze nodes that operate on typed state."""

    def input_discovery(self, state: AnalyzeGraphState) -> AnalyzeGraphState: ...

    def parse_transcript(self, state: AnalyzeGraphState) -> AnalyzeGraphState: ...

    def context_builder(self, state: AnalyzeGraphState) -> AnalyzeGraphState: ...

    def extract_outline(self, state: AnalyzeGraphState) -> AnalyzeGraphState: ...

    def build_timeline_seeds(self, state: AnalyzeGraphState) -> AnalyzeGraphState: ...

    def build_entity_hints(self, state: AnalyzeGraphState) -> AnalyzeGraphState: ...

    def draft_markdown(self, state: AnalyzeGraphState) -> AnalyzeGraphState: ...

    def qa_and_finalize(self, state: AnalyzeGraphState) -> AnalyzeGraphState: ...

    def qa_join(self, state: AnalyzeGraphState) -> AnalyzeGraphState: ...

    def write_ops_and_artifacts(self, state: AnalyzeGraphState) -> AnalyzeGraphState: ...


class TypedComposeNodeImpl(Protocol):
    """Protocol for Compose nodes that operate on typed state."""

    def context_builder(self, state: ComposeGraphState) -> ComposeGraphState: ...

    def client_lane_draft(self, state: ComposeGraphState) -> ComposeGraphState: ...

    def client_lane_qa(self, state: ComposeGraphState) -> ComposeGraphState: ...

    def client_lane_editor(self, state: ComposeGraphState) -> ComposeGraphState: ...

    def client_lane_revise(self, state: ComposeGraphState) -> ComposeGraphState: ...

    def lawyer_lane_draft(self, state: ComposeGraphState) -> ComposeGraphState: ...

    def lawyer_lane_qa(self, state: ComposeGraphState) -> ComposeGraphState: ...

    def lawyer_lane_editor(self, state: ComposeGraphState) -> ComposeGraphState: ...

    def lawyer_lane_revise(self, state: ComposeGraphState) -> ComposeGraphState: ...

    def qa_join(self, state: ComposeGraphState) -> ComposeGraphState: ...

    def write_release_artifacts(self, state: ComposeGraphState) -> ComposeGraphState: ...


class AnalyzeStateAdapter:
    """Adapter that bridges dict-based state mappings with AnalyzeGraphState."""

    def from_mapping(self, data: Mapping[str, object]) -> AnalyzeGraphState:
        metadata = _metadata_from_mapping(data)
        return AnalyzeGraphState(
            metadata=metadata,
            transcript_path=_coerce_path(data.get("transcript_path")),
            transcript_text=_coerce_str(data.get("transcript_text")),
            outline=_coerce_json_optional(data.get("outline")),
            timeline_events=_coerce_timeline_events(data.get("timeline_events")),
            entity_hints=_coerce_entity_hints(data.get("entity_hints")),
            summary_markdown=_coerce_str(data.get("summary_markdown")),
            summary_json=_coerce_json_optional(data.get("summary_json")),
            lane_payloads=_coerce_stage_payloads(data.get("lane_payloads")),
            metrics=_coerce_metrics(data.get("metrics")),
            artifacts=_coerce_artifacts(data.get("artifacts")),
            ops_records=_coerce_ops_records(data.get("ops_records")),
        )

    def into_mapping(
        self,
        state: AnalyzeGraphState,
        data: StateMapping | None = None,
    ) -> StateMapping:
        mapping = data or {}
        _apply_metadata(state.metadata, mapping)
        mapping["transcript_path"] = state.transcript_path
        mapping["transcript_text"] = state.transcript_text
        mapping["outline"] = state.outline
        mapping["timeline_events"] = state.timeline_events
        mapping["entity_hints"] = state.entity_hints
        mapping["summary_markdown"] = state.summary_markdown
        mapping["summary_json"] = state.summary_json
        mapping["lane_payloads"] = _stage_payloads_to_mapping(state.lane_payloads)
        mapping["metrics"] = _metrics_to_mapping(state.metrics)
        mapping["artifacts"] = state.artifacts
        mapping["ops_records"] = state.ops_records
        return mapping


class ComposeStateAdapter:
    """Adapter that bridges dict-based state mappings with ComposeGraphState."""

    def from_mapping(self, data: Mapping[str, object]) -> ComposeGraphState:
        metadata = _metadata_from_mapping(data)
        return ComposeGraphState(
            metadata=metadata,
            summary_json=_coerce_json_optional(data.get("summary_json")),
            client_markdown=_coerce_str(data.get("client_markdown")),
            lawyer_markdown=_coerce_str(data.get("lawyer_markdown")),
            qa_report=_coerce_json_optional(data.get("qa_report")),
            lane_payloads=_coerce_stage_payloads(data.get("lane_payloads")),
            metrics=_coerce_metrics(data.get("metrics")),
            artifacts=_coerce_artifacts(data.get("artifacts")),
            ops_records=_coerce_ops_records(data.get("ops_records")),
        )

    def into_mapping(
        self,
        state: ComposeGraphState,
        data: StateMapping | None = None,
    ) -> StateMapping:
        mapping = data or {}
        _apply_metadata(state.metadata, mapping)
        mapping["summary_json"] = state.summary_json
        mapping["client_markdown"] = state.client_markdown
        mapping["lawyer_markdown"] = state.lawyer_markdown
        mapping["qa_report"] = state.qa_report
        mapping["lane_payloads"] = _stage_payloads_to_mapping(state.lane_payloads)
        mapping["metrics"] = _metrics_to_mapping(state.metrics)
        mapping["artifacts"] = state.artifacts
        mapping["ops_records"] = state.ops_records
        return mapping


def adapt_analyze_impl(
    typed_impl: TypedAnalyzeNodeImpl,
    *,
    adapter: AnalyzeStateAdapter | None = None,
) -> AnalyzeNodeImpl:
    """Wrap a typed Analyze implementation so LangGraph can invoke it."""

    state_adapter = adapter or AnalyzeStateAdapter()

    class _Adapter:
        """Dynamic adapter populated with LangGraph-compatible methods."""


    for method_name in _ANALYZE_METHODS:
        method = _typed_analyze_callable(typed_impl, method_name)
        setattr(_Adapter, method_name, _wrap_analyze_method(method, state_adapter))

    return cast("AnalyzeNodeImpl", _Adapter())


def adapt_compose_impl(
    typed_impl: TypedComposeNodeImpl,
    *,
    adapter: ComposeStateAdapter | None = None,
) -> ComposeNodeImpl:
    """Wrap a typed Compose implementation so LangGraph can invoke it."""

    state_adapter = adapter or ComposeStateAdapter()

    class _Adapter:
        """Dynamic adapter populated with LangGraph-compatible methods."""


    for method_name in _COMPOSE_METHODS:
        method = _typed_compose_callable(typed_impl, method_name)
        setattr(_Adapter, method_name, _wrap_compose_method(method, state_adapter))

    return cast("ComposeNodeImpl", _Adapter())


def _typed_analyze_callable(
    impl: TypedAnalyzeNodeImpl,
    method_name: str,
) -> Callable[[AnalyzeGraphState], AnalyzeGraphState]:
    method = getattr(impl, method_name)
    return cast("Callable[[AnalyzeGraphState], AnalyzeGraphState]", method)


def _wrap_analyze_method(
    method: Callable[[AnalyzeGraphState], AnalyzeGraphState],
    state_adapter: AnalyzeStateAdapter,
) -> Callable[[StateMapping], StateMapping]:
    def _invoke(self: object, state: StateMapping) -> StateMapping:  # noqa: ARG001 - binder for descriptor
        typed_state = state_adapter.from_mapping(state)
        updated = method(typed_state)
        return state_adapter.into_mapping(updated, state)

    return _invoke


def _typed_compose_callable(
    impl: TypedComposeNodeImpl,
    method_name: str,
) -> Callable[[ComposeGraphState], ComposeGraphState]:
    method = getattr(impl, method_name)
    return cast("Callable[[ComposeGraphState], ComposeGraphState]", method)


def _wrap_compose_method(
    method: Callable[[ComposeGraphState], ComposeGraphState],
    state_adapter: ComposeStateAdapter,
) -> Callable[[StateMapping], StateMapping]:
    def _invoke(self: object, state: StateMapping) -> StateMapping:  # noqa: ARG001 - binder for descriptor
        typed_state = state_adapter.from_mapping(state)
        updated = method(typed_state)
        return state_adapter.into_mapping(updated, state)

    return _invoke


def _metadata_from_mapping(data: Mapping[str, object]) -> RunMetadata:
    case_id = _coerce_case_id(data.get("case_id"))
    job_id = _coerce_job_id(data.get("job_id"))
    if case_id is None or job_id is None:
        msg = "LangGraph state missing required case_id/job_id metadata"
        raise KeyError(msg)
    return RunMetadata(
        case_id=case_id,
        job_id=job_id,
        org_id=_coerce_org_id(data.get("org_id")),
        case_dir=_coerce_path(data.get("case_dir")),
        settings_snapshot_sha=_coerce_str(data.get("settings_snapshot_sha")),
    )


def _apply_metadata(metadata: RunMetadata, mapping: StateMapping) -> None:
    mapping["case_id"] = metadata.case_id
    mapping["job_id"] = metadata.job_id
    mapping["org_id"] = metadata.org_id
    mapping["case_dir"] = metadata.case_dir
    mapping["settings_snapshot_sha"] = metadata.settings_snapshot_sha


def _coerce_case_id(value: object) -> CaseID | None:
    if isinstance(value, str) and value:
        return CaseID(value)
    return None


def _coerce_job_id(value: object) -> JobID | None:
    if isinstance(value, str) and value:
        return JobID(value)
    return None


def _coerce_org_id(value: object) -> OrganizationID | None:
    if isinstance(value, str) and value:
        return OrganizationID(value)
    return None


def _coerce_path(value: object) -> Path | None:
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value:
        return Path(value)
    return None


def _coerce_str(value: object) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _coerce_json_optional(value: object) -> JSONObject | None:
    if value is None:
        return None
    return coerce_json_object(value)


def _coerce_stage_payloads(value: object) -> dict[StageKey, JSONObject]:
    if isinstance(value, dict):
        payloads: dict[StageKey, JSONObject] = {}
        for raw_key, raw in value.items():
            try:
                stage_key = StageKey(str(raw_key))
            except ValueError:
                continue
            payloads[stage_key] = coerce_json_object(raw)
        return payloads
    if isinstance(value, Mapping):
        mapping_value = cast("Mapping[object, object]", value)
        payloads = {}
        for raw_key, raw in mapping_value.items():
            try:
                stage_key = StageKey(str(raw_key))
            except ValueError:
                continue
            payloads[stage_key] = coerce_json_object(raw)
        return payloads
    return {}


def _stage_payloads_to_mapping(payloads: Mapping[StageKey, JSONObject]) -> dict[str, JSONObject]:
    return {stage.value: payload for stage, payload in payloads.items()}


def _coerce_timeline_events(value: object) -> tuple[TimelineEvent, ...]:
    if isinstance(value, tuple) and all(isinstance(item, TimelineEvent) for item in value):
        return value
    events: list[TimelineEvent] = []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence = cast("Sequence[object]", value)
        for item in sequence:
            if isinstance(item, TimelineEvent):
                events.append(item)
            elif isinstance(item, Mapping):
                mapping_item = cast("Mapping[str, object]", item)
                uuid = str(mapping_item.get("uuid") or "")
                label = str(mapping_item.get("label") or "")
                summary = str(mapping_item.get("summary") or "")
                speaker_value = mapping_item.get("speaker")
                speaker = None
                if isinstance(speaker_value, str):
                    trimmed_speaker = speaker_value.strip()
                    speaker = trimmed_speaker or None
                start_raw = mapping_item.get("start_time_s")
                start_time = float(start_raw) if isinstance(start_raw, (int, float)) else None
                refs_value = mapping_item.get("evidence_refs")
                refs = _coerce_evidence_refs(refs_value)
                events.append(
                    TimelineEvent(
                        uuid=uuid,
                        label=label,
                        summary=summary,
                        speaker=speaker,
                        start_time_s=start_time,
                        evidence_refs=refs,
                    ),
                )
    return tuple(events)


def _coerce_entity_hints(value: object) -> tuple[EntityHint, ...]:
    if isinstance(value, tuple) and all(isinstance(item, EntityHint) for item in value):
        return value
    hints: list[EntityHint] = []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence = cast("Sequence[object]", value)
        for item in sequence:
            if isinstance(item, EntityHint):
                hints.append(item)
            elif isinstance(item, Mapping):
                mapping_item = cast("Mapping[str, object]", item)
                uuid = str(mapping_item.get("uuid") or "")
                name = str(mapping_item.get("name") or "")
                entity_type = str(mapping_item.get("entity_type") or "")
                refs = _coerce_evidence_refs(mapping_item.get("evidence_refs"))
                hints.append(
                    EntityHint(
                        uuid=uuid,
                        name=name,
                        entity_type=entity_type,
                        evidence_refs=refs,
                    ),
                )
    return tuple(hints)


def _coerce_evidence_refs(value: object) -> tuple[str, ...]:
    if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
        return value
    refs: list[str] = []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence = cast("Sequence[object]", value)
        for entry in sequence:
            if isinstance(entry, str):
                stripped = entry.strip()
                if stripped:
                    refs.append(stripped)
    return tuple(refs)


def _coerce_metrics(value: object) -> dict[StageKey, ProviderCallMetrics]:
    if not isinstance(value, Mapping):
        return {}
    mapping_value = cast("Mapping[object, object]", value)
    metrics: dict[StageKey, ProviderCallMetrics] = {}
    for raw_key, raw_metrics in mapping_value.items():
        try:
            stage_key = StageKey(str(raw_key))
        except ValueError:
            continue
        metrics[stage_key] = _coerce_metric(raw_metrics)
    return metrics


def _coerce_metric(value: object) -> ProviderCallMetrics:
    if isinstance(value, ProviderCallMetrics):
        return value
    total = _coerce_int(value, "total_tokens")
    prompt = _coerce_int(value, "prompt_tokens")
    completion = _coerce_int(value, "completion_tokens")
    latency = _coerce_float(value, "latency_ms")
    return ProviderCallMetrics(
        total_tokens=total,
        prompt_tokens=prompt,
        completion_tokens=completion,
        latency_ms=latency,
    )


def _metrics_to_mapping(
    metrics: Mapping[StageKey, ProviderCallMetrics],
) -> dict[str, ProviderCallMetrics]:
    return {stage.value: metric for stage, metric in metrics.items()}


def _coerce_int(value: object, key: str) -> int | None:
    if isinstance(value, ProviderCallMetrics):
        attribute = getattr(value, key, None)
        return cast("int | None", attribute)
    if isinstance(value, Mapping):
        mapping_value = cast("Mapping[str, object]", value)
        candidate = mapping_value.get(key)
    else:
        candidate = None
    if isinstance(candidate, int):
        return candidate
    if isinstance(candidate, float):
        return int(candidate)
    return None


def _coerce_float(value: object, key: str) -> float | None:
    if isinstance(value, ProviderCallMetrics):
        attribute = getattr(value, key, None)
        return cast("float | None", attribute)
    if isinstance(value, Mapping):
        mapping_value = cast("Mapping[str, object]", value)
        candidate = mapping_value.get(key)
    else:
        candidate = None
    if isinstance(candidate, (int, float)):
        return float(candidate)
    return None


def _coerce_artifacts(value: object) -> tuple[ArtifactRef, ...]:
    if isinstance(value, tuple) and all(isinstance(item, ArtifactRef) for item in value):
        return value
    refs: list[ArtifactRef] = []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence = cast("Sequence[object]", value)
        for item in sequence:
            if isinstance(item, ArtifactRef):
                refs.append(item)
            elif isinstance(item, Mapping):
                mapping_item = cast("Mapping[str, object]", item)
                kind = str(mapping_item.get("kind") or "")
                path_value = mapping_item.get("path")
                path = _coerce_path(path_value)
                checksum_value = mapping_item.get("checksum")
                checksum = str(checksum_value) if isinstance(checksum_value, str) else None
                if kind and path is not None:
                    refs.append(ArtifactRef(kind=kind, path=path, checksum=checksum))
    return tuple(refs)


def _coerce_ops_records(value: object) -> tuple[OpsRecord, ...]:
    if isinstance(value, tuple) and all(isinstance(item, OpsRecord) for item in value):
        return value
    records: list[OpsRecord] = []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence = cast("Sequence[object]", value)
        for item in sequence:
            if isinstance(item, OpsRecord):
                records.append(item)
            elif isinstance(item, Mapping):
                mapping_item = cast("Mapping[str, object]", item)
                name = str(mapping_item.get("name") or "")
                payload = coerce_json_object(mapping_item.get("payload", {}))
                raw_stage = mapping_item.get("stage_key")
                stage_key = None
                if raw_stage is not None:
                    try:
                        stage_key = StageKey(str(raw_stage))
                    except ValueError:
                        stage_key = None
                if name:
                    records.append(OpsRecord(name=name, payload=payload, stage_key=stage_key))
    return tuple(records)


__all__ = [
    "AnalyzeGraphState",
    "AnalyzeStateAdapter",
    "ArtifactRef",
    "ComposeGraphState",
    "ComposeStateAdapter",
    "OpsRecord",
    "RunMetadata",
    "TypedAnalyzeNodeImpl",
    "TypedComposeNodeImpl",
    "adapt_analyze_impl",
    "adapt_compose_impl",
]
