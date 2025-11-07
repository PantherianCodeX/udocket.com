# pyright: strict

"""Low-level client Protocols for provider adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from packages.ai.api import ChatRequest, ChatResult, EmbeddingRequest, EmbeddingResult
else:  # pragma: no cover - runtime placeholders
    class _RuntimeTypeStub:
        """Fallback type used only when annotations are evaluated at runtime."""

    ChatRequest = ChatResult = EmbeddingRequest = EmbeddingResult = _RuntimeTypeStub


@runtime_checkable
class ChatClient(Protocol):
    """Protocol for chat-completion style providers."""

    def invoke(self, request: ChatRequest) -> ChatResult: ...


@runtime_checkable
class EmbeddingClient(Protocol):
    """Protocol for embedding providers."""

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult: ...


__all__ = ["ChatClient", "EmbeddingClient"]
