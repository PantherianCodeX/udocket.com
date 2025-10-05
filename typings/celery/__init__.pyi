# pyright: reportUnusedImport=false, reportUnusedClass=false, reportUnusedFunction=false, reportUnusedVariable=false
# mypy: ignore-errors

from typing import Any, Callable, Protocol, TypeVar, overload

_T = TypeVar("_T", bound=Callable[..., Any])

class TaskProtocol(Protocol):
    request: Any

@overload
def shared_task(__func: _T) -> _T: ...

@overload
def shared_task(*, bind: bool = ...) -> Callable[[_T], _T]: ...

@overload
def shared_task(__func: None = ..., *, bind: bool = ...) -> Callable[[_T], _T]: ...

class Celery: ...

