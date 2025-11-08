from __future__ import annotations

from typing import Any, Mapping


class Response:
    def __init__(self, data: Mapping[str, Any] | Any, status: int | None = ..., **kwargs: Any) -> None: ...
