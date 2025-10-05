# pyright: reportUnusedImport=false, reportUnusedClass=false, reportUnusedFunction=false, reportUnusedVariable=false
# mypy: ignore-errors

from __future__ import annotations

from typing import Any, Mapping


class Response:
    data: Any
    status_code: int
    def __init__(self, data: Any = ..., status: int | None = ..., headers: Mapping[str, str] | None = ...) -> None: ...


__all__ = ["Response"]

