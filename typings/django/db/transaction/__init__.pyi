from __future__ import annotations

from typing import Any, Callable, ContextManager, TypeVar, overload
from types import TracebackType

_T = TypeVar("_T")
_F = TypeVar("_F", bound=Callable[..., Any])


class Atomic(ContextManager[None]):
    def __enter__(self) -> None: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...

    def __call__(self, func: _F) -> _F: ...


@overload
def atomic(func: _F) -> _F: ...


@overload
def atomic(using: str | None = ..., savepoint: bool | None = ...) -> Atomic: ...


def on_commit(func: Callable[[], Any]) -> None: ...
