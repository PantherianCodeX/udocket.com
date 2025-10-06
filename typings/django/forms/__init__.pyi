from __future__ import annotations

from typing import Any, TypeVar, Generic

_M = TypeVar("_M")

class Form:
    pass

class ModelForm(Form, Generic[_M]):
    fields: Any
    class Meta:
        model: Any
    def __class_getitem__(cls, item: Any) -> Any: ...

__all__ = ["Form", "ModelForm"]
