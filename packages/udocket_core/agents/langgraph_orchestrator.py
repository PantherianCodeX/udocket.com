from __future__ import annotations

import logging
import os
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

    logging.getLogger("udocket.summarize.agent").debug(
        "langgraph.compile.start",
        extra={"nodes": [
            "input_discovery",
            "parse_transcript",
            "context_builder",
            "extract_outline",
            "build_timeline_seeds",
            "build_entity_hints",
            "draft_markdown",
            "qa_and_finalize",
            "write_ops_and_artifacts",
        ]},
    )
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

    compiled = graph.compile()
    logging.getLogger("udocket.summarize.agent").debug(
        "langgraph.compile.complete",
        extra={"entry": "input_discovery", "node_count": len(node_order)},
    )
    return SummarizeGraph(compiled, entry="input_discovery", nodes=node_order)


_LANGGRAPH_DEBUG_ENV = {"1", "true", "yes", "on"}
_LANGGRAPH_TRACE_ENV = "LANGGRAPH_DEBUG"
_LANGGRAPH_DEBUG_INITIALIZED = False


def enable_langgraph_debug_logging(force: bool = False) -> None:
    """Ensure langgraph/langchain loggers emit DEBUG output to the console.

    This respects the :envvar:`LANGGRAPH_DEBUG` flag and can also be forced
    programmatically when a caller enables verbose summarizer tracing.
    """

    global _LANGGRAPH_DEBUG_INITIALIZED
    if _LANGGRAPH_DEBUG_INITIALIZED:
        return

    env_flag = os.getenv(_LANGGRAPH_TRACE_ENV, "").strip().lower() in _LANGGRAPH_DEBUG_ENV
    if not (force or env_flag):
        return

    root_logger = logging.getLogger()
    if root_logger.level > logging.DEBUG:
        root_logger.setLevel(logging.DEBUG)

    for name in (
        "langgraph",
        "langchain",
        "langchain_core",
        "langchain.text_splitter",
        "langchain.schema",
        "udocket.summarize.pipeline",
        "udocket.summarize.agent",
    ):
        scoped_logger = logging.getLogger(name)
        if scoped_logger.level > logging.DEBUG:
            scoped_logger.setLevel(logging.DEBUG)
        scoped_logger.propagate = True

    _LANGGRAPH_DEBUG_INITIALIZED = True


__all__ = [
    "SummarizeGraph",
    "SummarizeNodeImpl",
    "build_summarize_graph",
    "enable_langgraph_debug_logging",
]
