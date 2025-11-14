from __future__ import annotations

from typing import Any

class RetrieveModelMixin:
    def retrieve(self, request: Any, *args: Any, **kwargs: Any) -> Any: ...

class ListModelMixin:
    def list(self, request: Any, *args: Any, **kwargs: Any) -> Any: ...

__all__ = ["RetrieveModelMixin", "ListModelMixin"]
