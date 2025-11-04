from __future__ import annotations

from datetime import datetime, tzinfo


def now() -> datetime: ...


def make_aware(value: datetime, timezone: tzinfo | None = ...) -> datetime: ...


def localtime(value: datetime | None = ..., timezone: tzinfo | None = ...) -> datetime: ...
