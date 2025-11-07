from __future__ import annotations

# pyright: strict

"""Low-level client Protocols for provider adapters."""

from typing import Protocol, runtime_checkable

from ..api import (
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
)


@runtime_checkable
class ChatClient(Protocol):
    """Protocol for chat-completion style providers."""

    def invoke(self, request: ChatRequest) -> ChatResult: ...


@runtime_checkable
class EmbeddingClient(Protocol):
    """Protocol for embedding providers."""

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult: ...


__all__ = ["ChatClient", "EmbeddingClient"]
