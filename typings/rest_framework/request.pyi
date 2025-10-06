from __future__ import annotations

from typing import Any, Mapping

class Request:
    method: str
    data: Any
    query_params: Mapping[str, Any]
    user: Any

__all__ = ["Request"]

