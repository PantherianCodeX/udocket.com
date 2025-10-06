from __future__ import annotations

from typing import Any, Generic, TypeVar

_M = TypeVar("_M")

class BaseInlineFormSet(Generic[_M]):
    def save(self, *args: Any, **kwargs: Any) -> Any: ...
    def __class_getitem__(cls, item: Any) -> Any: ...

class ModelChoiceField(Generic[_M]):
    queryset: Any
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

__all__ = ["BaseInlineFormSet", "ModelChoiceField"]
