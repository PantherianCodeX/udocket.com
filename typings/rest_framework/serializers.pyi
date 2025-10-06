from __future__ import annotations

from typing import Any

class Serializer:
    @property
    def data(self) -> Any: ...

class ModelSerializer(Serializer):
    pass

__all__ = ["Serializer", "ModelSerializer"]

