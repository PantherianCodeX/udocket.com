# pyright: strict
"""Tests for automation.langgraph.types adapters and state models."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from packages.ai.types import CaseID, JobID, OrganizationID, ProviderCallMetrics
from packages.common.agents.stage_map import StageKey

from automation.langgraph.types import (
    AnalyzeGraphState,
    AnalyzeStateAdapter,
    ComposeGraphState,
    ComposeStateAdapter,
    RunMetadata,
    TypedAnalyzeNodeImpl,
    TypedComposeNodeImpl,
    adapt_analyze_impl,
    adapt_compose_impl,
)


def _run_metadata() -> RunMetadata:
    return RunMetadata(
        case_id=CaseID("case-1"),
        job_id=JobID("job-1"),
        org_id=OrganizationID("org-1"),
        case_dir=Path("/tmp/case-1"),
        settings_snapshot_sha="sha-123",
    )


def test_analyze_state_adapter_round_trip() -> None:
    adapter = AnalyzeStateAdapter()
    metrics = ProviderCallMetrics(
        total_tokens=10,
        prompt_tokens=4,
        completion_tokens=6,
        latency_ms=12.5,
    )
    original = AnalyzeGraphState(
        metadata=_run_metadata(),
        transcript_path=Path("/tmp/transcript.json"),
        transcript_text="hello",
        outline={"sections": []},
        lane_payloads={StageKey.AN_INPUT_DISCOVERY: {"ok": True}},
        metrics={StageKey.AN_ATOMS_EXTRACT: metrics},
    )

    mapping = adapter.into_mapping(original, {})
    restored = adapter.from_mapping(mapping)

    assert restored.metadata.case_id == original.metadata.case_id
    assert restored.metadata.job_id == original.metadata.job_id
    assert restored.transcript_path == original.transcript_path
    assert restored.transcript_text == original.transcript_text
    assert restored.outline == original.outline
    assert StageKey.AN_INPUT_DISCOVERY in restored.lane_payloads
    assert StageKey.AN_ATOMS_EXTRACT in restored.metrics


def test_compose_state_adapter_round_trip() -> None:
    adapter = ComposeStateAdapter()
    metrics = ProviderCallMetrics(
        total_tokens=5,
        prompt_tokens=2,
        completion_tokens=3,
        latency_ms=8.0,
    )
    original = ComposeGraphState(
        metadata=_run_metadata(),
        summary_json={"summary": "ok"},
        client_markdown="client",
        lawyer_markdown="lawyer",
        lane_payloads={StageKey.CO_CONTEXT_BUILD: {"ctx": True}},
        metrics={StageKey.CO_CONTEXT_BUILD: metrics},
    )

    mapping = adapter.into_mapping(original, {})
    restored = adapter.from_mapping(mapping)

    assert restored.metadata.case_id == original.metadata.case_id
    assert restored.summary_json == original.summary_json
    assert restored.client_markdown == original.client_markdown
    assert restored.lawyer_markdown == original.lawyer_markdown
    assert StageKey.CO_CONTEXT_BUILD in restored.lane_payloads
    assert StageKey.CO_CONTEXT_BUILD in restored.metrics


def test_adapt_analyze_impl_invokes_typed_methods() -> None:
    class Impl:
        def __init__(self) -> None:
            self.called: list[str] = []

        def input_discovery(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
            self.called.append("input_discovery")
            return state

        def parse_transcript(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
            self.called.append("parse_transcript")
            return state

        def context_builder(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
            self.called.append("context_builder")
            return state

        def extract_outline(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
            self.called.append("extract_outline")
            return state

        def build_timeline_seeds(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
            self.called.append("build_timeline_seeds")
            return state

        def build_entity_hints(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
            self.called.append("build_entity_hints")
            return state

        def draft_markdown(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
            self.called.append("draft_markdown")
            return state

        def qa_and_finalize(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
            self.called.append("qa_and_finalize")
            return state

        def qa_join(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
            self.called.append("qa_join")
            return state

        def write_ops_and_artifacts(self, state: AnalyzeGraphState) -> AnalyzeGraphState:
            self.called.append("write_ops_and_artifacts")
            return state

    typed_impl = cast(TypedAnalyzeNodeImpl, Impl())
    adapter = adapt_analyze_impl(typed_impl)

    # adapter methods accept a mutable mapping (LangGraph-style) and update it in place
    state: dict[str, object] = {
        "case_id": "case-1",
        "job_id": "job-1",
    }
    adapter.input_discovery(state)
    adapter.parse_transcript(state)

    assert "input_discovery" in typed_impl.called
    assert "parse_transcript" in typed_impl.called


def test_adapt_compose_impl_invokes_typed_methods() -> None:
    class Impl:
        def __init__(self) -> None:
            self.called: list[str] = []

        def context_builder(self, state: ComposeGraphState) -> ComposeGraphState:
            self.called.append("context_builder")
            return state

        def client_lane_draft(self, state: ComposeGraphState) -> ComposeGraphState:
            self.called.append("client_lane_draft")
            return state

        def client_lane_qa(self, state: ComposeGraphState) -> ComposeGraphState:
            self.called.append("client_lane_qa")
            return state

        def client_lane_editor(self, state: ComposeGraphState) -> ComposeGraphState:
            self.called.append("client_lane_editor")
            return state

        def client_lane_revise(self, state: ComposeGraphState) -> ComposeGraphState:
            self.called.append("client_lane_revise")
            return state

        def lawyer_lane_draft(self, state: ComposeGraphState) -> ComposeGraphState:
            self.called.append("lawyer_lane_draft")
            return state

        def lawyer_lane_qa(self, state: ComposeGraphState) -> ComposeGraphState:
            self.called.append("lawyer_lane_qa")
            return state

        def lawyer_lane_editor(self, state: ComposeGraphState) -> ComposeGraphState:
            self.called.append("lawyer_lane_editor")
            return state

        def lawyer_lane_revise(self, state: ComposeGraphState) -> ComposeGraphState:
            self.called.append("lawyer_lane_revise")
            return state

        def qa_join(self, state: ComposeGraphState) -> ComposeGraphState:
            self.called.append("qa_join")
            return state

        def write_release_artifacts(self, state: ComposeGraphState) -> ComposeGraphState:
            self.called.append("write_release_artifacts")
            return state

    typed_impl = cast(TypedComposeNodeImpl, Impl())
    adapter = adapt_compose_impl(typed_impl)

    state: dict[str, object] = {
        "case_id": "case-1",
        "job_id": "job-1",
    }
    adapter.context_builder(state)
    adapter.client_lane_draft(state)

    assert "context_builder" in typed_impl.called
    assert "client_lane_draft" in typed_impl.called

