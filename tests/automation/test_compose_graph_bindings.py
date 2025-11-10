from __future__ import annotations

import pytest

from automation.langgraph.compose_graph import build_compose_graph_v1, get_compose_stage_bindings
from packages.common.agents import StageKey, StagePlan, StageSpec
from packages.ai.types import AgentTask
from packages.core.agents.langgraph_orchestrator import ComposeGraph
from tests.automation.langgraph_fakes import fake_state_graph_factory


def test_compose_stage_bindings_cover_required_nodes() -> None:
    bindings = get_compose_stage_bindings()
    stage_keys = {binding.stage_key for binding in bindings}
    assert StageKey.CO_CONTEXT_BUILD in stage_keys
    assert StageKey.CO_CLIENT_DRAFT in stage_keys
    assert StageKey.CO_RELEASE_WRITE in stage_keys


def test_compose_stage_bindings_unique_methods() -> None:
    bindings = get_compose_stage_bindings()
    method_names = [binding.method_name for binding in bindings]
    assert len(method_names) == len(set(method_names))


def test_get_compose_stage_bindings_unknown_stage_raises() -> None:
    custom_plan = StagePlan(
        ordered=(
            StageSpec(stage_key=StageKey.CO_CONTEXT_BUILD, agent_task=None),
            StageSpec(stage_key=StageKey.AN_INPUT_DISCOVERY, agent_task=AgentTask.GENERATE),
        ),
    )
    with pytest.raises(KeyError):
        get_compose_stage_bindings(stage_plan=custom_plan)


class _DummyComposeImpl:
    def __init__(self) -> None:
        self.history: list[str] = []

    def context_builder(self, state: dict[str, object]) -> dict[str, object]:
        self.history.append("context_builder")
        state.setdefault("history", []).append("context_builder")  # type: ignore[call-arg]
        return state

    def client_lane_draft(self, state: dict[str, object]) -> dict[str, object]:
        self.history.append("client_lane_draft")
        state["history"].append("client_lane_draft")  # type: ignore[index]
        return state

    def client_lane_qa(self, state: dict[str, object]) -> dict[str, object]:
        self.history.append("client_lane_qa")
        state["history"].append("client_lane_qa")  # type: ignore[index]
        return state

    def client_lane_editor(self, state: dict[str, object]) -> dict[str, object]:
        self.history.append("client_lane_editor")
        state["history"].append("client_lane_editor")  # type: ignore[index]
        return state

    def client_lane_revise(self, state: dict[str, object]) -> dict[str, object]:
        self.history.append("client_lane_revise")
        state["history"].append("client_lane_revise")  # type: ignore[index]
        return state

    def lawyer_lane_draft(self, state: dict[str, object]) -> dict[str, object]:
        self.history.append("lawyer_lane_draft")
        state["history"].append("lawyer_lane_draft")  # type: ignore[index]
        return state

    def lawyer_lane_qa(self, state: dict[str, object]) -> dict[str, object]:
        self.history.append("lawyer_lane_qa")
        state["history"].append("lawyer_lane_qa")  # type: ignore[index]
        return state

    def lawyer_lane_editor(self, state: dict[str, object]) -> dict[str, object]:
        self.history.append("lawyer_lane_editor")
        state["history"].append("lawyer_lane_editor")  # type: ignore[index]
        return state

    def lawyer_lane_revise(self, state: dict[str, object]) -> dict[str, object]:
        self.history.append("lawyer_lane_revise")
        state["history"].append("lawyer_lane_revise")  # type: ignore[index]
        return state

    def qa_join(self, state: dict[str, object]) -> dict[str, object]:
        self.history.append("qa_join")
        state["history"].append("qa_join")  # type: ignore[index]
        return state

    def write_release_artifacts(self, state: dict[str, object]) -> dict[str, object]:
        self.history.append("write_release_artifacts")
        state["history"].append("write_release_artifacts")  # type: ignore[index]
        return state


def test_build_compose_graph_v1_returns_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_impl = _DummyComposeImpl()

    monkeypatch.setattr(
        "automation.langgraph.compose_graph.STATE_GRAPH_FACTORY",
        fake_state_graph_factory,
    )
    monkeypatch.setattr(
        "automation.langgraph.compose_graph.LANGGRAPH_END",
        "__end__",
    )

    graph = build_compose_graph_v1(dummy_impl)
    assert isinstance(graph, ComposeGraph)
    result = graph.invoke({"history": []})
    assert result["history"][0] == "context_builder"  # type: ignore[index]
    assert result["history"][-1] == "write_release_artifacts"  # type: ignore[index]
