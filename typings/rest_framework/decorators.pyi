from __future__ import annotations

from typing import Any, Callable, Iterable, TypeVar

from rest_framework.response import Response


F = TypeVar("F", bound=Callable[..., Response])


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

