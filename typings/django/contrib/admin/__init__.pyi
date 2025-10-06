from __future__ import annotations

from typing import Any, TypeVar, Callable

_T = TypeVar("_T")

class AdminSite:
    site_header: str
    site_title: str
    index_title: str

class ModelAdmin:
    form: Any
    def get_form(self, request: Any, obj: Any | None = ..., **kwargs: Any) -> Any: ...
    def save_model(self, request: Any, obj: Any, form: Any, change: bool) -> None: ...

class TabularInline:
    pass

def register(model_or_iterable: Any) -> Callable[[_T], _T]: ...
def display(*args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...

site: AdminSite

__all__ = ["AdminSite", "ModelAdmin", "TabularInline", "register", "site"]
