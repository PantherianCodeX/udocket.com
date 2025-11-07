# pyright: strict
"""Provider interface definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ..api import (
        ChatRequest,
        ChatResult,
        ComposeRequest,
        ComposeResult,
        EmbeddingRequest,
        EmbeddingResult,
        EntityExtractionRequest,
        EntityExtractionResult,
        SummarizeRequest,
        SummarizeResult,
        TimelineExtractionRequest,
        TimelineExtractionResult,
    )
    from ..types import AgentTask, Region
    from ..types.identifiers import ModelName, ProviderName, RouteName


@runtime_checkable
class ProviderAdapter(Protocol):
    """Abstract provider adapter exposed to routing/clients."""

    @property
    def name(self) -> ProviderName: ...

    @property
    def region(self) -> Region: ...

    @property
    def supported_tasks(self) -> tuple[AgentTask, ...]: ...

    def available_models(self, task: AgentTask) -> tuple[ModelName, ...]: ...

    def summarize(self, request: SummarizeRequest) -> SummarizeResult: ...

    def compose(self, request: ComposeRequest) -> ComposeResult: ...

    def extract_timeline(
        self,
        request: TimelineExtractionRequest,
    ) -> TimelineExtractionResult: ...

    def extract_entities(
        self,
        request: EntityExtractionRequest,
    ) -> EntityExtractionResult: ...

    def describe_route(self, *, task: AgentTask, model: ModelName) -> RouteName | None: ...

    def chat(self, request: ChatRequest) -> ChatResult: ...

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult: ...


__all__ = ["ProviderAdapter"]
