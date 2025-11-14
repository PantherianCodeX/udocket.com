from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, ContextManager, ParamSpec, TypeVar, overload

_P = ParamSpec("_P")
_R = TypeVar("_R")


@overload
def fixture(func: Callable[_P, _R]) -> Callable[_P, _R]: ...


@overload
def fixture(
    *,
    scope: str | None = ...,
    autouse: bool = ...,
    name: str | None = ...,
) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]: ...


@overload
def fixture(
    func: Callable[_P, _R],
    *,
    scope: str | None = ...,
    autouse: bool = ...,
    name: str | None = ...,
) -> Callable[_P, _R]: ...


class MonkeyPatch:
    @overload
    def setattr(self, target: str, value: Any, /) -> None: ...

    @overload
    def setattr(self, target: object, name: str, value: Any, /) -> None: ...

    def setenv(self, name: str, value: str, *, prepend: bool = ...) -> None: ...

    def getenv(self, name: str, default: Any | None = ...) -> Any: ...

    def delenv(self, name: str, *, raising: bool = ...) -> None: ...

def raises(
    expected_exception: type[BaseException] | tuple[type[BaseException], ...],
    match: str | None = ...,
) -> ContextManager[Any]: ...


class _Mark:
    def parametrize(
        self,
        argnames: str | tuple[str, ...],
        argvalues: Iterable[tuple[Any, ...]] | Iterable[Any],
        **kwargs: Any,
    ) -> Callable[[Callable[..., object]], Callable[..., object]]: ...


mark: _Mark


__all__ = ["fixture", "MonkeyPatch", "raises", "mark"]
