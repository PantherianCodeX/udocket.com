# pyright: reportUnusedImport=false, reportUnusedClass=false, reportUnusedFunction=false, reportUnusedVariable=false
# mypy: ignore-errors

from __future__ import annotations

from typing import Any, Dict


class Serializer:
    context: Dict[str, Any]
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def to_representation(self, instance: Any) -> Dict[str, Any]: ...


__all__ = ["Serializer"]

