from __future__ import annotations

# pyright: strict

import importlib
import importlib.util
import logging
import os
from dataclasses import dataclass, field
from typing import Callable, MutableMapping, Protocol, cast

State = MutableMapping[str, object]
NodeCallable = Callable[[State], State | None]


class _CompiledGraphProtocol(Protocol):
    def invoke(self, state: State) -> State:
        ...


class _StateGraphProtocol(Protocol):
    def add_node(self, name: str, fn: NodeCallable) -> None:
        ...

    def set_entry_point(self, name: str) -> None:
        ...

    def add_edge(self, source: str, target: object) -> None:
        ...

    def compile(self) -> _CompiledGraphProtocol:
        ...


StateGraphFactory = Callable[[type[MutableMapping[str, object]]], _StateGraphProtocol]


_langgraph_spec = importlib.util.find_spec("langgraph.graph")
if _langgraph_spec is not None:  # pragma: no cover - optional dependency
    _langgraph_module = importlib.import_module("langgraph.graph")
    _runtime_end = getattr(_langgraph_module, "END", None)
    _runtime_state_graph = getattr(_langgraph_module, "StateGraph", None)
else:  # pragma: no cover - optional dependency missing
    _runtime_end = None
    _runtime_state_graph = None

LANGGRAPH_END: object | None = _runtime_end
STATE_GRAPH_FACTORY: StateGraphFactory | None = (
    cast(StateGraphFactory, _runtime_state_graph)
    if _runtime_state_graph is not None
    else None
)


class AnalyzeNodeImpl(Protocol):
    def input_discovery(self, state: State) -> State | None:
        ...

    def parse_transcript(self, state: State) -> State | None:
        ...

    def context_builder(self, state: State) -> State | None:
        ...

    def extract_outline(self, state: State) -> State | None:
        ...

    def build_timeline_seeds(self, state: State) -> State | None:
        ...

    def build_entity_hints(self, state: State) -> State | None:
        ...

    def draft_markdown(self, state: State) -> State | None:
        ...

    def qa_and_finalize(self, state: State) -> State | None:
        ...

    def write_ops_and_artifacts(self, state: State) -> State | None:
        ...


@dataclass(frozen=True)
class AnalyzeGraph:
    graph: _CompiledGraphProtocol
    entry: str = "input_discovery"
    nodes: tuple[str, ...] = field(default_factory=tuple)

    def invoke(self, state: State | None = None) -> State:
        if not hasattr(self.graph, "invoke"):
            raise RuntimeError(
                "LangGraph not available; install langgraph to use this orchestrator"
            )
        starter: State = dict(state) if state is not None else {}
        return self.graph.invoke(starter)


_NODE_ORDER = (
    "input_discovery",
    "parse_transcript",
    "context_builder",
    "extract_outline",
    "build_timeline_seeds",
    "build_entity_hints",
    "draft_markdown",
    "qa_and_finalize",
    "write_ops_and_artifacts",
)


def build_analyze_graph(impl: AnalyzeNodeImpl) -> AnalyzeGraph:
    """Compile a LangGraph state machine for the Analyze pipeline."""

    if STATE_GRAPH_FACTORY is None or LANGGRAPH_END is None:
        raise RuntimeError("langgraph not installed")

    logging.getLogger("udocket.analyze.agent").debug(
        "langgraph.compile.start",
        extra={"nodes": list(_NODE_ORDER)},
    )

    graph = STATE_GRAPH_FACTORY(dict)

    for node_name in _NODE_ORDER:
        fn: NodeCallable = getattr(impl, node_name)
        graph.add_node(node_name, fn)

    graph.set_entry_point(_NODE_ORDER[0])
    for current, nxt in zip(_NODE_ORDER, _NODE_ORDER[1:]):
        graph.add_edge(current, nxt)
    graph.add_edge(_NODE_ORDER[-1], LANGGRAPH_END)

    compiled = graph.compile()
    logging.getLogger("udocket.analyze.agent").debug(
        "langgraph.compile.complete",
        extra={"entry": _NODE_ORDER[0], "node_count": len(_NODE_ORDER)},
    )
    return AnalyzeGraph(compiled, entry=_NODE_ORDER[0], nodes=_NODE_ORDER)


_LANGGRAPH_DEBUG_ENV = {"1", "true", "yes", "on"}
_LANGGRAPH_TRACE_ENV = "LANGGRAPH_DEBUG"
_langgraph_debug_initialized = False


def enable_langgraph_debug_logging(force: bool = False) -> None:
    """Ensure langgraph/langchain loggers emit DEBUG output to the console."""

    global _langgraph_debug_initialized
    if _langgraph_debug_initialized:
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
        "udocket.analyze.pipeline",
        "udocket.analyze.agent",
    ):
        scoped_logger = logging.getLogger(name)
        if scoped_logger.level > logging.DEBUG:
            scoped_logger.setLevel(logging.DEBUG)
        scoped_logger.propagate = True

    _langgraph_debug_initialized = True


__all__ = [
    "AnalyzeGraph",
    "AnalyzeNodeImpl",
    "build_analyze_graph",
    "enable_langgraph_debug_logging",
]
