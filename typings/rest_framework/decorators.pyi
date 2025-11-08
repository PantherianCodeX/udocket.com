# pyright: reportUnusedImport=false, reportUnusedClass=false, reportUnusedFunction=false, reportUnusedVariable=false
# mypy: ignore-errors

from __future__ import annotations

from typing import Any, Callable, Iterable, TypeVar


F = TypeVar("F", bound=Callable[..., Any])


def action(
    *,
    methods: Iterable[str] | None = ...,
    detail: bool = ...,
    url_path: str | None = ...,
    url_name: str | None = ...,
    **kwargs: Any,
) -> Callable[[F], F]:
    ...


__all__ = ["action"]
