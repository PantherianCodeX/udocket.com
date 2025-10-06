from __future__ import annotations

from typing import Any

class DefaultRouter:
    urls: list[object]

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def register(self, prefix: str, viewset: type[Any], basename: str | None = ...) -> None: ...
