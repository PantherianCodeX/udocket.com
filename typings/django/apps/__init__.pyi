from __future__ import annotations

from typing import Any


class AppConfig:
    name: str
    label: str
    verbose_name: str

    def __init__(self, app_name: str, app_module: Any) -> None: ...

    def ready(self) -> None: ...


__all__ = ["AppConfig"]

