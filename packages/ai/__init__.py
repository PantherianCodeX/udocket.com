"""Public surface for the ai package."""

from __future__ import annotations

from importlib import metadata as _metadata

from .api import (
    AIClient,
    ChatMessage,
    ChatRequest,
    ChatResult,
    ComposeAudience,
    ComposeRequest,
    ComposeResult,
    EmbeddingRequest,
    EmbeddingResult,
    EmbeddingVector,
    EntityExtractionRequest,
    EntityExtractionResult,
    EntityHint,
    SummarizeRequest,
    SummarizeResult,
    TimelineEvent,
    TimelineExtractionRequest,
    TimelineExtractionResult,
    chat,
    compose,
    embed,
    extract_entities,
    extract_timeline,
    summarize,
)
from .client import DefaultAIClient
from .config import AISettings, CapabilityLimit, ModelRoute, ProviderAccount
from .registry import build_client
from .types import AgentTask, CaseContext, LanguageCode

try:  # pragma: no cover - fallback for editable installs
    __version__ = _metadata.version("udocket_ai")
except _metadata.PackageNotFoundError:  # pragma: no cover - local checkout
    __version__ = "0.0.0"

__all__ = [
    "AIClient",
    "AISettings",
    "AgentTask",
    "CapabilityLimit",
    "CaseContext",
    "ChatMessage",
    "ChatRequest",
    "ChatResult",
    "ComposeAudience",
    "ComposeRequest",
    "ComposeResult",
    "DefaultAIClient",
    "EmbeddingRequest",
    "EmbeddingResult",
    "EmbeddingVector",
    "EntityExtractionRequest",
    "EntityExtractionResult",
    "EntityHint",
    "LanguageCode",
    "ModelRoute",
    "ProviderAccount",
    "SummarizeRequest",
    "SummarizeResult",
    "TimelineEvent",
    "TimelineExtractionRequest",
    "TimelineExtractionResult",
    "__version__",
    "build_client",
    "chat",
    "compose",
    "embed",
    "extract_entities",
    "extract_timeline",
    "summarize",
]
