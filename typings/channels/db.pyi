# pyright: reportUnusedImport=false, reportUnusedClass=false, reportUnusedFunction=false, reportUnusedVariable=false
# mypy: ignore-errors

from __future__ import annotations

from typing import Awaitable, Callable, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")

def database_sync_to_async(
    func: Callable[P, T], *, thread_sensitive: bool = ...
) -> Callable[P, Awaitable[T]]: ...
