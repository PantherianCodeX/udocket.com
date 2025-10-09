from __future__ import annotations

# pyright: strict

import logging
from typing import Mapping


class ContextualFormatter(logging.Formatter):
    """Formatter that injects default values for structured logging fields."""

    def __init__(
        self,
        fmt: str,
        datefmt: str | None = None,
        *,
        defaults: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt)
        self._defaults = dict(defaults or {})

    def format(self, record: logging.LogRecord) -> str:
        for key, value in self._defaults.items():
            if not hasattr(record, key):
                setattr(record, key, value)
        return super().format(record)


__all__ = ["ContextualFormatter"]
