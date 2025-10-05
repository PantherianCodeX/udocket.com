# pyright: reportUnusedImport=false, reportUnusedClass=false, reportUnusedFunction=false, reportUnusedVariable=false
# mypy: ignore-errors

from __future__ import annotations

from typing import Any, Iterable, Iterator, Mapping

from django.utils.datastructures import MultiValueDict


class QueryDict(MultiValueDict[str, Any]):
    ...


class HttpHeaders(dict[str, str]):
    ...


class HttpRequest:
    GET: QueryDict
    POST: QueryDict
    COOKIES: dict[str, str]
    META: dict[str, Any]
    FILES: MultiValueDict[str, Any]
    method: str | None
    path: str
    path_info: str
    resolver_match: Any
    user: Any
    session: Any
    headers: HttpHeaders

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    def get_host(self) -> str: ...

    def get_full_path(self, force_append_slash: bool = ...) -> str: ...

    def build_absolute_uri(self, location: str | None = ...) -> str: ...

    def is_secure(self) -> bool: ...

    def read(self, n: int | None = -1) -> bytes: ...

    def readline(self, limit: int | None = -1) -> bytes: ...

    def __iter__(self) -> Iterator[bytes]: ...

    def readlines(self) -> list[bytes]: ...


class HttpResponse:
    ...


__all__ = ["HttpRequest", "HttpHeaders", "QueryDict", "HttpResponse"]

