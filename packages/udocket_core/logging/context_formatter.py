from __future__ import annotations

# pyright: strict

import logging
from typing import Mapping


class ContextualFormatter(logging.Formatter):
    """Formatter that appends contextual fields only when they are present."""

    def __init__(
        self,
        fmt: str,
        datefmt: str | None = None,
        *,
        defaults: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt)
        self._defaults = dict(defaults or {})
        self._ordered_keys = tuple(self._defaults.keys())

    def format(self, record: logging.LogRecord) -> str:
        context_segments: list[str] = []
        for key in self._ordered_keys:
            default_value = self._defaults.get(key)
            if not hasattr(record, key):
                setattr(record, key, default_value)
                continue

            current_value = getattr(record, key)
            if current_value in (None, "", default_value):
                setattr(record, key, default_value)
                continue

            normalized = str(current_value)
            setattr(record, key, normalized)
            context_segments.append(f"{key}={normalized}")

        record.context_suffix = ""
        if context_segments:
            record.context_suffix = f" [{' '.join(context_segments)}]"

        return super().format(record)


__all__ = ["ContextualFormatter"]
