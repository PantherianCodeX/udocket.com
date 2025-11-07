"""Deterministic UUID helpers for AI artifacts."""

from __future__ import annotations

# pyright: strict
import uuid

from packages.ai.types import UUIDStr

NAMESPACE_AI = uuid.uuid5(uuid.NAMESPACE_DNS, "ai.udocket.com")


def deterministic_uuid(*, namespace: str, content: str) -> UUIDStr:
    """Return a deterministic UUID5 for the given namespace + content."""

    seed = f"{namespace}:{content}"
    return UUIDStr(str(uuid.uuid5(NAMESPACE_AI, seed)))


__all__ = ["NAMESPACE_AI", "deterministic_uuid"]
