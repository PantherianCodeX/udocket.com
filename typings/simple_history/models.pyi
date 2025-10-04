from __future__ import annotations

from typing import Any, Generic, TypeVar

from django.db.models import Manager, Model

_T = TypeVar("_T", bound=Model)


class HistoryManager(Manager[_T], Generic[_T]):
    ...


class HistoricalRecords(Generic[_T]):
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    def __get__(self, instance: _T | None, owner: type[_T]) -> HistoryManager[_T]: ...
