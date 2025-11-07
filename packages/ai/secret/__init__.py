# pyright: strict

"""Secret source abstractions for provider adapters."""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable


@runtime_checkable
class SecretSource(Protocol):
    """Provides access to stored credentials without exposing storage details."""

    def get(self, name: str) -> str | None: ...


class EnvSecretSource:
    """Secret source backed by environment variables."""

    def get(self, name: str) -> str | None:
        value = os.getenv(name, "").strip()
        return value or None


__all__ = ["EnvSecretSource", "SecretSource"]
