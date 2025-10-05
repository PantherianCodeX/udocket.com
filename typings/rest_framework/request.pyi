# pyright: reportUnusedImport=false, reportUnusedClass=false, reportUnusedFunction=false, reportUnusedVariable=false
# mypy: ignore-errors

from __future__ import annotations

from typing import Any, Mapping


class Request:
    user: Any
    data: Mapping[str, Any]
    query_params: Mapping[str, Any]


__all__ = ["Request"]

