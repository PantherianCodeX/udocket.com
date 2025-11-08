from __future__ import annotations

from typing import Any, Callable


def async_to_sync(func: Callable[..., Any]) -> Callable[..., Any]: ...
