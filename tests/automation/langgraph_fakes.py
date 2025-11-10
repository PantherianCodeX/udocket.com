from __future__ import annotations

from collections.abc import Callable
from collections.abc import MutableMapping

State = MutableMapping[str, object]


class FakeStateGraph:
    """Minimal in-memory graph that executes nodes sequentially."""

    def __init__(self) -> None:
        self._order: list[str] = []
        self._callables: dict[str, Callable[[State], State | None]] = {}
        self.entry: str | None = None

    def add_node(self, name: str, fn: Callable[[State], State | None]) -> None:
        self._order.append(name)
        self._callables[name] = fn

    def set_entry_point(self, name: str) -> None:
        self.entry = name

    def add_edge(self, source: str, target: object) -> None:  # noqa: ARG002 - interface contract
        # The fake graph only cares about node order for testing so edges are ignored.
        return None

    def compile(self) -> FakeCompiledGraph:
        if not self.entry and self._order:
            self.entry = self._order[0]
        return FakeCompiledGraph(tuple(self._order), dict(self._callables))


class FakeCompiledGraph:
    """Compiled graph that simply invokes nodes in the recorded order."""

    def __init__(
        self,
        order: tuple[str, ...],
        callables: dict[str, Callable[[State], State | None]],
    ) -> None:
        self._order = order
        self._callables = callables

    def invoke(self, state: State) -> State:
        current = state
        for name in self._order:
            fn = self._callables[name]
            result = fn(current)
            if result is not None:
                current = result
        return current


def fake_state_graph_factory(_state_type: type[MutableMapping[str, object]]) -> FakeStateGraph:
    return FakeStateGraph()


__all__ = ["FakeCompiledGraph", "FakeStateGraph", "fake_state_graph_factory"]
