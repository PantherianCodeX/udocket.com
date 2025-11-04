from __future__ import annotations

from typing import Any, Awaitable, Callable, TypeVar

_T = TypeVar("_T")


def database_sync_to_async(func: Callable[..., _T]) -> Callable[..., Awaitable[_T]]: ...
