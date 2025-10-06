from __future__ import annotations

from typing import Any

class URLPattern:
    pattern: Any

class URLResolver:
    url_patterns: list[Any]

def path(route: str, view: Any, *args: Any, **kwargs: Any) -> URLPattern: ...
def include(arg: Any, namespace: str | None = ...) -> tuple[list[Any], str | None, str | None]: ...
def reverse(viewname: Any, urlconf: Any = ..., args: Any = ..., kwargs: Any = ..., current_app: Any = ..., *, query: Any = ..., fragment: Any = ...) -> str: ...

__all__ = ["URLPattern", "URLResolver", "path", "include", "reverse"]

