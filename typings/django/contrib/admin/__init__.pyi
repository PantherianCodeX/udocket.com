from __future__ import annotations

from typing import Any, Iterable, TypeVar


T_co = TypeVar("T_co", covariant=True)


class ModelAdmin:
    list_display: Iterable[str]
    list_filter: Iterable[str]
    search_fields: Iterable[str]

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...


class AdminSite:
    def register(self, model: type[Any], admin_class: type[ModelAdmin] | None = ...) -> type[ModelAdmin]: ...


admin = AdminSite()


def register(model: type[Any]) -> type[ModelAdmin]: ...


__all__ = ["ModelAdmin", "admin", "register"]
