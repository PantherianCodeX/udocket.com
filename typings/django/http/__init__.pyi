from __future__ import annotations

from typing import Any, Mapping

class QueryDict(Mapping[str, Any]):
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def get(self, key: str, default: Any | None = ...) -> Any | None: ...
    def getlist(self, key: str) -> list[Any]: ...

class HttpRequest:
    method: str
    user: Any
    GET: QueryDict
    POST: QueryDict
    META: Mapping[str, Any]
    FILES: Mapping[str, Any]
    headers: Mapping[str, str]
    content_type: str
    body: bytes

class HttpResponse:
    status_code: int
    content: Any
    def __init__(self, content: Any = ..., status: int | None = ..., content_type: str | None = ..., headers: Mapping[str, str] | None = ...) -> None: ...

class JsonResponse(HttpResponse):
    pass

class HttpResponseRedirect(HttpResponse):
    pass

class Http404(Exception):
    pass

__all__ = [
    "HttpRequest",
    "HttpResponse",
    "HttpResponseRedirect",
    "JsonResponse",
    "Http404",
]
