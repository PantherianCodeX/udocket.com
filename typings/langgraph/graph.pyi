from __future__ import annotations

from typing import Any, Callable, Generic, Mapping, TypeVar

_T = TypeVar("_T")

START: str
END: str


class CompiledGraph(Generic[_T]):
    def invoke(self, state: _T) -> Any: ...
    async def ainvoke(self, state: _T) -> Any: ...


class StateGraph(Generic[_T]):
    def __init__(self, state_type: type[_T]) -> None: ...
    def add_node(self, name: str, node: Callable[..., Any]) -> None: ...
    def add_edge(self, source: str, target: str) -> None: ...
    def add_conditional_edges(
        self,
        source: str,
        router: Callable[..., str],
        routes: Mapping[str, str],
    ) -> None: ...
    def compile(self) -> CompiledGraph[_T]: ...
