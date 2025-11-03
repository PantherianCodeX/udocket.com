from __future__ import annotations

from typing import Any, Mapping, Iterator

class QueryDict(Mapping[str, Any]):
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def __iter__(self) -> Iterator[str]: ...
    def __len__(self) -> int: ...
    def __getitem__(self, key: str) -> Any: ...
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

class FileResponse(HttpResponse):
    def __init__(
        self,
        file: Any,
        as_attachment: bool = ...,
        filename: str | None = ...,
        content_type: str | None = ...,
        headers: Mapping[str, str] | None = ...,
    ) -> None: ...

class JsonResponse(HttpResponse):
    pass

class HttpResponseRedirect(HttpResponse):
    pass

class Http404(Exception):
    pass

__all__ = [
    "HttpRequest",
    "HttpResponse",
    "FileResponse",
    "HttpResponseRedirect",
    "JsonResponse",
    "Http404",
    "QueryDict",
]
