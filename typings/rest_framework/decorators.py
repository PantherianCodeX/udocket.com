from __future__ import annotations

from typing import Any, Callable


def action(func: Callable[..., Any] | None = ..., **kwargs: Any) -> Callable[..., Any]: ...
