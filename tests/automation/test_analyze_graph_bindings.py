from __future__ import annotations

import pytest

from automation.langgraph.analyze_graph import build_analyze_graph_v1, get_analyze_stage_bindings
from packages.common.agents import StageKey, StagePlan, StageSpec
from packages.ai.types import AgentTask
from packages.core.agents.langgraph_orchestrator import AnalyzeGraph

from tests.automation.langgraph_fakes import fake_state_graph_factory


def test_analyze_stage_bindings_cover_required_nodes() -> None:
    bindings = get_analyze_stage_bindings()
    stage_keys = {binding.stage_key for binding in bindings}
    assert StageKey.AN_INPUT_DISCOVERY in stage_keys
    assert StageKey.AN_SUMMARY_DRAFT in stage_keys
    assert StageKey.AN_FINALIZE_WRITE in stage_keys


def test_analyze_stage_bindings_use_unique_method_names() -> None:
    bindings = get_analyze_stage_bindings()
    method_names = [binding.method_name for binding in bindings]
    assert len(method_names) == len(set(method_names))


def test_get_analyze_stage_bindings_raises_on_missing_stage() -> None:
    custom_plan = StagePlan(
        ordered=(
            StageSpec(stage_key=StageKey.AN_INPUT_DISCOVERY, agent_task=None),
            StageSpec(stage_key=StageKey.AN_FLAGS_EXTRACT, agent_task=AgentTask.EXTRACT),
        ),
    )
    with pytest.raises(KeyError):
        get_analyze_stage_bindings(stage_plan=custom_plan)


class _DummyAnalyzeImpl:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def _record(self, name: str, state: dict[str, object]) -> dict[str, object]:
        self.calls.append(name)
        history = state.setdefault("history", [])
        if isinstance(history, list):
            history.append(name)
        return state

    def input_discovery(self, state: dict[str, object]) -> dict[str, object]:
        return self._record("input_discovery", state)

    def parse_transcript(self, state: dict[str, object]) -> dict[str, object]:
        return self._record("parse_transcript", state)

    def context_builder(self, state: dict[str, object]) -> dict[str, object]:
        return self._record("context_builder", state)

    def extract_outline(self, state: dict[str, object]) -> dict[str, object]:
        return self._record("extract_outline", state)

    def build_timeline_seeds(self, state: dict[str, object]) -> dict[str, object]:
        return self._record("build_timeline_seeds", state)

    def build_entity_hints(self, state: dict[str, object]) -> dict[str, object]:
        return self._record("build_entity_hints", state)

    def draft_markdown(self, state: dict[str, object]) -> dict[str, object]:
        return self._record("draft_markdown", state)

    def qa_and_finalize(self, state: dict[str, object]) -> dict[str, object]:
        return self._record("qa_and_finalize", state)

    def qa_join(self, state: dict[str, object]) -> dict[str, object]:
        return self._record("qa_join", state)

    def write_ops_and_artifacts(self, state: dict[str, object]) -> dict[str, object]:
        return self._record("write_ops_and_artifacts", state)


def test_build_analyze_graph_v1_executes_nodes(monkeypatch: pytest.MonkeyPatch) -> None:
    impl = _DummyAnalyzeImpl()
    monkeypatch.setattr(
        "automation.langgraph.analyze_graph.STATE_GRAPH_FACTORY",
        fake_state_graph_factory,
    )
    monkeypatch.setattr(
        "automation.langgraph.analyze_graph.LANGGRAPH_END",
        "__end__",
    )
    graph = build_analyze_graph_v1(impl)
    assert isinstance(graph, AnalyzeGraph)
    result = graph.invoke({"history": []})
    assert result["history"][0] == "input_discovery"  # type: ignore[index]
    assert result["history"][-1] == "write_ops_and_artifacts"  # type: ignore[index]
