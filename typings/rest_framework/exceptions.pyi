from __future__ import annotations

from typing import Any

class APIException(Exception):
    status_code: int
    default_detail: Any
    detail: Any

__all__ = ["APIException"]

