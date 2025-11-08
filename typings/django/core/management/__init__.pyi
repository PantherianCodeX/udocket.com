from __future__ import annotations

from typing import Any

from . import base


def call_command(name: str, *args: Any, **kwargs: Any) -> Any: ...

__all__ = ["base", "call_command"]
