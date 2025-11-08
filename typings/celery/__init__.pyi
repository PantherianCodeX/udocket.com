# pyright: reportUnusedImport=false, reportUnusedClass=false, reportUnusedFunction=false, reportUnusedVariable=false
# mypy: ignore-errors

from typing import Any, Callable, Iterable, Mapping, Protocol, TypeVar, overload

_T = TypeVar("_T", bound=Callable[..., Any])

class TaskProtocol(Protocol):
    request: Any

@overload
def shared_task(__func: _T) -> _T: ...

@overload
def shared_task(*, bind: bool = ...) -> Callable[[_T], _T]: ...

@overload
def shared_task(__func: None = ..., *, bind: bool = ...) -> Callable[[_T], _T]: ...

class CeleryConfig(Protocol):
    worker_send_task_events: bool
    task_send_sent_event: bool
    worker_hijack_root_logger: bool


class _Inspect:
    def active(self) -> Any: ...
    def reserved(self) -> Any: ...
    def scheduled(self) -> Any: ...


class _Control:
    def inspect(self) -> _Inspect | None: ...


class Celery:
    conf: CeleryConfig
    control: _Control

    def __init__(self, main: str, broker: str | None = ..., backend: str | None = ..., **kwargs: Any) -> None: ...
    def config_from_object(self, obj: str | object, *, namespace: str | None = ...) -> None: ...
    def autodiscover_tasks(self, packages: Iterable[str] | None = ..., related_name: str | None = ...) -> None: ...
    def task(self, *args: Any, **kwargs: Any) -> Callable[..., Any]: ...
