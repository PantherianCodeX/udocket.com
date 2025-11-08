# pyright: strict

"""Secret source abstractions for provider adapters."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Callable


@runtime_checkable
class SecretSource(Protocol):
    """Provides access to stored credentials without exposing storage details."""

    def get(self, name: str) -> str | None: ...


class EnvSecretSource:
    """Secret source backed by environment variables."""

    def __init__(self, loader: Callable[[str, str], str] | None = None) -> None:
        super().__init__()
        self._loader = loader or os.getenv

    def get(self, name: str) -> str | None:
        value = self._loader(name, "").strip()
        return value or None


__all__ = ["EnvSecretSource", "SecretSource"]
