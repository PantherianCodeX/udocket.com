from __future__ import annotations

from typing import TYPE_CHECKING

from automation.langgraph.types import (
    AnalyzeGraphState,
    AnalyzeStateAdapter,
    ArtifactRef,
    ComposeGraphState,
    ComposeStateAdapter,
    OpsRecord,
    TypedAnalyzeNodeImpl,
    TypedComposeNodeImpl,
    adapt_analyze_impl,
    adapt_compose_impl,
)
from packages.ai.types import CaseID, JobID, OrganizationID, ProviderCallMetrics
from packages.common.agents import StageKey

if TYPE_CHECKING:
    from pathlib import Path


def test_analyze_state_adapter_roundtrip(tmp_path: Path) -> None:
    adapter = AnalyzeStateAdapter()
    mapping = {
        "case_id": CaseID("case-1"),
        "job_id": JobID("job-2"),
        "org_id": OrganizationID("org-3"),
        "case_dir": tmp_path,
        "settings_snapshot_sha": "abc123",
        "transcript_path": tmp_path / "transcript.txt",
        "transcript_text": "hello world",
        "outline": {"sections": []},
        "timeline_events": [
            {
                "uuid": "evt-1",
                "label": "Event",
                "summary": "Summary",
                "speaker": "spk",
                "start_time_s": 12.5,
                "evidence_refs": ["t1"],
            },
        ],
        "entity_hints": [
            {
                "uuid": "ent-1",
                "name": "Entity",
                "entity_type": "person",
                "evidence_refs": ["doc"],
            },
        ],
        "summary_markdown": "# Summary",
        "summary_json": {"sections": []},
        "lane_payloads": {StageKey.AN_OUTLINE_DRAFT.value: {"ok": True}},
        "metrics": {
            StageKey.AN_OUTLINE_DRAFT.value: {
                "total_tokens": 100,
                "prompt_tokens": 60,
                "completion_tokens": 40,
                "latency_ms": 250.5,
            },
        },
        "artifacts": [
            {
                "kind": "summary_json",
                "path": tmp_path / "analysis/summary.json",
                "checksum": "deadbeef",
            },
        ],
        "ops_records": [
            {
                "name": "ops_summary",
                "payload": {"status": "ok"},
                "stage_key": StageKey.AN_SUMMARY_DRAFT.value,
            },
        ],
    }
    typed = adapter.from_mapping(mapping)
    assert typed.metadata.case_id == CaseID("case-1")
    assert typed.metadata.job_id == JobID("job-2")
    assert typed.timeline_events[0].label == "Event"
    assert typed.entity_hints[0].entity_type == "person"
    assert StageKey.AN_OUTLINE_DRAFT in typed.lane_payloads
    assert StageKey.AN_OUTLINE_DRAFT in typed.metrics
    roundtripped = adapter.into_mapping(typed, {})
    assert roundtripped["case_id"] == CaseID("case-1")
    assert roundtripped["job_id"] == JobID("job-2")
    assert isinstance(roundtripped["artifacts"][0], ArtifactRef)  # type: ignore[index]
    assert isinstance(roundtripped["ops_records"][0], OpsRecord)  # type: ignore[index]


def test_compose_state_adapter_roundtrip(tmp_path: Path) -> None:
    adapter = ComposeStateAdapter()
    mapping = {
        "case_id": CaseID("case-7"),
        "job_id": JobID("job-8"),
        "org_id": OrganizationID("org-9"),
        "case_dir": tmp_path,
        "summary_json": {"summary": "text"},
        "client_markdown": "# Client",
        "lawyer_markdown": "# Lawyer",
        "qa_report": {"status": "ok"},
        "lane_payloads": {StageKey.CO_CLIENT_DRAFT.value: {"ok": True}},
        "metrics": {
            StageKey.CO_CLIENT_DRAFT.value: ProviderCallMetrics(total_tokens=10),
        },
        "artifacts": [
            {
                "kind": "client_letter",
                "path": tmp_path / "docs/client.md",
                "checksum": "abc",
            },
        ],
        "ops_records": [
            {
                "name": "ops_compose",
                "payload": {"status": "draft"},
                "stage_key": StageKey.CO_CLIENT_DRAFT.value,
            },
        ],
    }
    typed = adapter.from_mapping(mapping)
    assert typed.metadata.case_id == CaseID("case-7")
    assert StageKey.CO_CLIENT_DRAFT in typed.lane_payloads
    assert StageKey.CO_CLIENT_DRAFT in typed.metrics
    roundtripped = adapter.into_mapping(typed, {})
    assert roundtripped["lawyer_markdown"] == "# Lawyer"
    assert isinstance(roundtripped["artifacts"][0], ArtifactRef)  # type: ignore[index]


class _TypedAnalyzeImpl(TypedAnalyzeNodeImpl):
    def __init__(self, artifact_path: Path) -> None:
        self._artifact_path = artifact_path

    def input_discovery(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
        new_artifact = ArtifactRef(kind="input", path=self._artifact_path, checksum="123")
        return AnalyzeGraphState(
            metadata=state.metadata,
            artifacts=(*state.artifacts, new_artifact),
        )

    def parse_transcript(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
        return state

    def context_builder(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
        return state

    def extract_outline(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
        return state

    def build_timeline_seeds(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
        return state

    def build_entity_hints(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
        return state

    def draft_markdown(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
        return state

    def qa_and_finalize(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
        return state

    def qa_join(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
        return state

    def write_ops_and_artifacts(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
        return state


class _TypedComposeImpl(TypedComposeNodeImpl):
    def context_builder(self, state: ComposeGraphState) -> ComposeGraphState:
        return ComposeGraphState(metadata=state.metadata, summary_json={"ok": True})

    def client_lane_draft(self, state: ComposeGraphState) -> ComposeGraphState:
        return state

    def client_lane_qa(self, state: ComposeGraphState) -> ComposeGraphState:
        return state

    def client_lane_editor(self, state: ComposeGraphState) -> ComposeGraphState:
        return state

    def client_lane_revise(self, state: ComposeGraphState) -> ComposeGraphState:
        return state

    def lawyer_lane_draft(self, state: ComposeGraphState) -> ComposeGraphState:
        return state

    def lawyer_lane_qa(self, state: ComposeGraphState) -> ComposeGraphState:
        return state

    def lawyer_lane_editor(self, state: ComposeGraphState) -> ComposeGraphState:
        return state

    def lawyer_lane_revise(self, state: ComposeGraphState) -> ComposeGraphState:
        return state

    def qa_join(self, state: ComposeGraphState) -> ComposeGraphState:
        return state

    def write_release_artifacts(self, state: ComposeGraphState) -> ComposeGraphState:
        return state


def test_adapt_analyze_impl_updates_mapping(tmp_path: Path) -> None:
    adapter = AnalyzeStateAdapter()
    typed_impl = _TypedAnalyzeImpl(tmp_path / "input.json")
    wrapped = adapt_analyze_impl(typed_impl, adapter=adapter)
    state = {
        "case_id": CaseID("case-10"),
        "job_id": JobID("job-11"),
        "case_dir": tmp_path,
    }
    result = wrapped.input_discovery(state)
    artifacts = result["artifacts"]  # type: ignore[index]
    assert isinstance(artifacts[0], ArtifactRef)


def test_adapt_compose_impl_updates_mapping(tmp_path: Path) -> None:
    adapter = ComposeStateAdapter()
    typed_impl = _TypedComposeImpl()
    wrapped = adapt_compose_impl(typed_impl, adapter=adapter)
    state = {
        "case_id": CaseID("case-12"),
        "job_id": JobID("job-13"),
        "case_dir": tmp_path,
    }
    result = wrapped.context_builder(state)
    assert result["summary_json"] == {"ok": True}
