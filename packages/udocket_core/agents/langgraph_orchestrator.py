from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, MutableMapping, Protocol

try:  # pragma: no cover - optional dependency
    from langgraph.graph import END, StateGraph
except Exception:  # pragma: no cover - graceful fallback
    END = None  # type: ignore[assignment]
    StateGraph = None  # type: ignore[assignment]


NodeCallable = Callable[[MutableMapping[str, Any]], MutableMapping[str, Any] | None]


class SummarizeNodeImpl(Protocol):
    def input_discovery(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any] | None: ...
    def parse_transcript(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any] | None: ...
    def context_builder(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any] | None: ...
    def extract_outline(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any] | None: ...
    def build_timeline_seeds(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any] | None: ...
    def build_entity_hints(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any] | None: ...
    def draft_markdown(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any] | None: ...
    def qa_and_finalize(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any] | None: ...
    def write_ops_and_artifacts(self, state: MutableMapping[str, Any]) -> MutableMapping[str, Any] | None: ...


@dataclass
class SummarizeGraph:
    graph: Any
    entry: str = "input_discovery"
    nodes: Iterable[str] = field(default_factory=lambda: [])

    def invoke(self, state: MutableMapping[str, Any] | None = None) -> MutableMapping[str, Any]:
        if not hasattr(self.graph, "invoke"):
            raise RuntimeError("LangGraph not available; install langgraph to use this orchestrator")
        starter = state or {}
        return self.graph.invoke(starter)


def build_summarize_graph(impl: SummarizeNodeImpl) -> SummarizeGraph:
    """Compile a LangGraph state machine for the Summarize pipeline.

    Raises:
        RuntimeError: if langgraph is not installed in the environment.
    """

    if StateGraph is None or END is None:
        raise RuntimeError("langgraph not installed")

    graph = StateGraph(dict)
    node_order = [
        "input_discovery",
        "parse_transcript",
        "context_builder",
        "extract_outline",
        "build_timeline_seeds",
        "build_entity_hints",
        "draft_markdown",
        "qa_and_finalize",
        "write_ops_and_artifacts",
    ]

    for node_name in node_order:
        fn: NodeCallable = getattr(impl, node_name)
        graph.add_node(node_name, fn)

    graph.set_entry_point("input_discovery")
    for current, nxt in zip(node_order, node_order[1:]):
        graph.add_edge(current, nxt)
    graph.add_edge(node_order[-1], END)

    return SummarizeGraph(graph.compile(), entry="input_discovery", nodes=node_order)


__all__ = ["SummarizeGraph", "SummarizeNodeImpl", "build_summarize_graph"]
