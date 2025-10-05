# pyright: reportUnusedImport=false, reportUnusedClass=false, reportUnusedFunction=false, reportUnusedVariable=false
# mypy: ignore-errors

from __future__ import annotations

from typing import Any


class ViewSet:
    queryset: Any
    serializer_class: Any

    def get_queryset(self) -> Any: ...
    def get_serializer(self, *args: Any, **kwargs: Any) -> Any: ...


__all__ = ["ViewSet"]

