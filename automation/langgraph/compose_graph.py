# pyright: strict
"""LangGraph builder that follows the canonical Compose stage plan."""

from __future__ import annotations

import itertools
import logging

from packages.common.agents import COMPOSE_V1_STAGE_PLAN, StageKey, StagePlan
from packages.core.agents.langgraph_orchestrator import (
    LANGGRAPH_END,
    STATE_GRAPH_FACTORY,
    ComposeGraph,
    ComposeNodeImpl,
)

from .bindings import StageBinding, resolve_stage_bindings

logger = logging.getLogger("automation.langgraph.compose")

_STAGE_METHOD_MAP: dict[StageKey, str] = {
    StageKey.CO_CONTEXT_BUILD: "context_builder",
    StageKey.CO_CLIENT_DRAFT: "client_lane_draft",
    StageKey.CO_CLIENT_QA: "client_lane_qa",
    StageKey.CO_CLIENT_EDITOR: "client_lane_editor",
    StageKey.CO_CLIENT_REVISE: "client_lane_revise",
    StageKey.CO_LAWYER_DRAFT: "lawyer_lane_draft",
    StageKey.CO_LAWYER_QA: "lawyer_lane_qa",
    StageKey.CO_LAWYER_EDITOR: "lawyer_lane_editor",
    StageKey.CO_LAWYER_REVISE: "lawyer_lane_revise",
    StageKey.CO_QA_JOIN: "qa_join",
    StageKey.CO_RELEASE_WRITE: "write_release_artifacts",
}


def get_compose_stage_bindings(stage_plan: StagePlan | None = None) -> list[StageBinding]:
    """Return bindings between StageKeys and Compose node methods."""

    plan = stage_plan or COMPOSE_V1_STAGE_PLAN
    return resolve_stage_bindings(plan, _STAGE_METHOD_MAP)


def build_compose_graph_v1(
    impl: ComposeNodeImpl,
    *,
    stage_plan: StagePlan | None = None,
) -> ComposeGraph:
    """Compile the Compose LangGraph according to the canonical StagePlan."""

    if STATE_GRAPH_FACTORY is None or LANGGRAPH_END is None:
        msg = "langgraph not installed"
        raise RuntimeError(msg)

    bindings = get_compose_stage_bindings(stage_plan)
    graph = STATE_GRAPH_FACTORY(dict)
    node_names: list[str] = []
    for binding in bindings:
        node_callable = getattr(impl, binding.method_name)
        graph.add_node(binding.method_name, node_callable)
        node_names.append(binding.method_name)
        logger.debug(
            "compose.stage.bound",
            extra={"stage_key": binding.stage_key.value, "method": binding.method_name},
        )

    if not node_names:
        msg = "Compose StagePlan produced no executable stages"
        raise RuntimeError(msg)

    graph.set_entry_point(node_names[0])
    for current, nxt in itertools.pairwise(node_names):
        graph.add_edge(current, nxt)
    graph.add_edge(node_names[-1], LANGGRAPH_END)

    compiled = graph.compile()
    return ComposeGraph(graph=compiled, entry=node_names[0], nodes=tuple(node_names))


__all__ = ["StageBinding", "build_compose_graph_v1", "get_compose_stage_bindings"]
