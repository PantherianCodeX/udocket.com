# pyright: reportUnusedImport=false, reportUnusedClass=false, reportUnusedFunction=false, reportUnusedVariable=false
# mypy: ignore-errors

from __future__ import annotations

from typing import Mapping


class HttpResponse:
    status_code: int
    content: bytes


class HttpResponseRedirect(HttpResponse):
    url: str


__all__ = ["HttpResponse", "HttpResponseRedirect"]

