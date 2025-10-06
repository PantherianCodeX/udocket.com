from __future__ import annotations

from typing import Any, Mapping

class HttpRequest:
    method: str
    user: Any
    GET: Mapping[str, Any]
    POST: Mapping[str, Any]

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

