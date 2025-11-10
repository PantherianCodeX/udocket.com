# pyright: strict
"""LangGraph builder that follows the canonical Analyze stage plan."""

from __future__ import annotations

import itertools
import logging

from packages.common.agents import ANALYZE_V1_STAGE_PLAN, StageKey, StagePlan
from packages.core.agents.langgraph_orchestrator import (
    LANGGRAPH_END,
    STATE_GRAPH_FACTORY,
    AnalyzeGraph,
    AnalyzeNodeImpl,
)

from .bindings import StageBinding, resolve_stage_bindings

logger = logging.getLogger("automation.langgraph.analyze")


_STAGE_METHOD_MAP: dict[StageKey, str] = {
    StageKey.AN_INPUT_DISCOVERY: "input_discovery",
    StageKey.AN_ATOMS_EXTRACT: "parse_transcript",
    StageKey.AN_CONTEXT_BUILD: "context_builder",
    StageKey.AN_OUTLINE_DRAFT: "extract_outline",
    StageKey.AN_TIMELINE_BUILD: "build_timeline_seeds",
    StageKey.AN_ENTITIES_EXTRACT: "build_entity_hints",
    StageKey.AN_SUMMARY_DRAFT: "draft_markdown",
    StageKey.AN_LANE_QA: "qa_and_finalize",
    StageKey.AN_QA_JOIN: "qa_join",
    StageKey.AN_FINALIZE_WRITE: "write_ops_and_artifacts",
}


def _resolve_stage_bindings(stage_plan: StagePlan) -> list[StageBinding]:
    return resolve_stage_bindings(stage_plan, _STAGE_METHOD_MAP)


def build_analyze_graph_v1(
    impl: AnalyzeNodeImpl,
    *,
    stage_plan: StagePlan | None = None,
) -> AnalyzeGraph:
    """Compile the Analyze LangGraph according to the canonical StagePlan."""

    if STATE_GRAPH_FACTORY is None or LANGGRAPH_END is None:
        msg = "langgraph not installed"
        raise RuntimeError(msg)

    bindings = get_analyze_stage_bindings(stage_plan)
    graph = STATE_GRAPH_FACTORY(dict)
    node_names: list[str] = []
    for binding in bindings:
        node_callable = getattr(impl, binding.method_name)
        graph.add_node(binding.method_name, node_callable)
        node_names.append(binding.method_name)
        logger.debug(
            "analyze.stage.bound",
            extra={"stage_key": binding.stage_key.value, "method": binding.method_name},
        )

    if not node_names:
        msg = "Analyze StagePlan produced no executable stages"
        raise RuntimeError(msg)

    graph.set_entry_point(node_names[0])
    for current, nxt in itertools.pairwise(node_names):
        graph.add_edge(current, nxt)
    graph.add_edge(node_names[-1], LANGGRAPH_END)

    compiled = graph.compile()
    return AnalyzeGraph(graph=compiled, entry=node_names[0], nodes=tuple(node_names))


def get_analyze_stage_bindings(stage_plan: StagePlan | None = None) -> list[StageBinding]:
    """Return bindings between StageKeys and Analyze node methods."""

    plan = stage_plan or ANALYZE_V1_STAGE_PLAN
    return _resolve_stage_bindings(plan)


__all__ = ["StageBinding", "build_analyze_graph_v1", "get_analyze_stage_bindings"]
