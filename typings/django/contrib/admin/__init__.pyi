# pyright: reportUnusedImport=false, reportUnusedClass=false, reportUnusedFunction=false, reportUnusedVariable=false
# mypy: ignore-errors

from __future__ import annotations

from typing import Any, Callable, Iterable, Protocol, TypeVar

_ModelT = TypeVar("_ModelT", bound=object)


class InlineModelAdmin:
    model: type[Any] | None
    extra: int
    autocomplete_fields: Iterable[str]

    def __init__(self, model: type[Any], admin_site: AdminSite | None = ...) -> None: ...


class TabularInline(InlineModelAdmin):
    ...


class ModelAdmin:
    model: type[Any] | None
    form: type[Any]
    add_form: type[Any]
    inlines: Iterable[type[InlineModelAdmin]]
    list_display: Iterable[str]
    list_filter: Iterable[str]
    search_fields: Iterable[str]
    readonly_fields: Iterable[str]

    def __init__(self, model: type[Any], admin_site: AdminSite | None = ...) -> None: ...
    def get_form(self, request: Any, obj: Any | None = ..., change: bool = ..., **kwargs: Any) -> type[Any]: ...
    def save_model(self, request: Any, obj: Any, form: Any, change: bool) -> None: ...
    def save_formset(self, request: Any, form: Any | None, formset: Any, change: bool) -> None: ...
    def get_readonly_fields(self, request: Any, obj: Any | None = ...) -> Iterable[str]: ...
    def get_queryset(self, request: Any) -> Any: ...


class AdminSite:
    def register(self, model: type[Any], admin_class: type[ModelAdmin] | None = ..., **options: Any) -> None: ...
    def admin_view(self, view: Callable[..., Any], cacheable: bool = ...) -> Callable[..., Any]: ...
    def get_urls(self) -> Iterable[Any]: ...
    def each_context(self, request: Any) -> dict[str, Any]: ...


class _AdminNamespace(Protocol):
    site: AdminSite


admin: _AdminNamespace
site: AdminSite


def register(model: type[Any], admin_class: type[ModelAdmin] | None = ..., **options: Any) -> Callable[[type[ModelAdmin]], type[ModelAdmin]]: ...


def display(*, description: str | None = ...) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...


__all__ = [
    "AdminSite",
    "ModelAdmin",
    "TabularInline",
    "InlineModelAdmin",
    "admin",
    "site",
    "register",
    "display",
]
