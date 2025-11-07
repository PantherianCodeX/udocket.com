from __future__ import annotations

# pyright: strict

"""Secret source abstractions for provider adapters."""

import os
from typing import Protocol


class SecretSource(Protocol):
    """Provides access to stored credentials without exposing storage details."""

    def get(self, name: str) -> str | None: ...


class EnvSecretSource:
    """Secret source backed by environment variables."""

    def get(self, name: str) -> str | None:
        value = os.getenv(name, "").strip()
        return value or None


__all__ = ["SecretSource", "EnvSecretSource"]
