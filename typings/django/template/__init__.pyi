from __future__ import annotations

from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

class Library:
    def filter(self, name: str | None = ..., filter_func: F | None = ..., **kwargs: Any) -> Callable[[F], F]: ...
    def simple_tag(self, func: F | None = ..., takes_context: bool = ...) -> Callable[[F], F]: ...
    def inclusion_tag(self, filename: str, func: F | None = ..., takes_context: bool = ...) -> Callable[[F], F]: ...

__all__ = ["Library"]
