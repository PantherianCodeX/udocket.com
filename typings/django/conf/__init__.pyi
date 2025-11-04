from __future__ import annotations

from typing import Any


class _SettingsProtocol:
    def __getattr__(self, name: str) -> Any: ...


settings: _SettingsProtocol

__all__ = ["settings"]

