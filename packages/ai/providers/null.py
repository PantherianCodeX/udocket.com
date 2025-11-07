from __future__ import annotations

# pyright: strict

"""Deterministic no-op provider used in tests."""

from collections.abc import Collection
from dataclasses import dataclass, field

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
from .interfaces import ProviderAdapter


@dataclass(slots=True)
class NullProvider(ProviderAdapter):
    """Provider that returns empty payloads for deterministic tests."""

    _name: ProviderName = field(default_factory=lambda: ProviderName("null-provider"))
    _region: Region = Region("test-region")

    @property
    def name(self) -> ProviderName:
        return self._name

    @property
    def region(self) -> Region:
        return self._region

    @property
    def supported_tasks(self) -> Collection[AgentTask]:
        return tuple(AgentTask)

    def available_models(self, task: AgentTask) -> Collection[ModelName]:
        return (ModelName("null-model"),)

    def summarize(self, request: SummarizeRequest) -> SummarizeResult:
        return SummarizeResult(summary_text="", metrics=None)

    def compose(self, request: ComposeRequest) -> ComposeResult:
        return ComposeResult()

    def extract_timeline(
        self, request: TimelineExtractionRequest
    ) -> TimelineExtractionResult:
        return TimelineExtractionResult(events=(), metrics=None)

    def extract_entities(
        self, request: EntityExtractionRequest
    ) -> EntityExtractionResult:
        return EntityExtractionResult(entities=(), metrics=None)

    def describe_route(self, *, task: AgentTask, model: ModelName) -> RouteName | None:
        return RouteName(f"{task.value}:{model}")

    def chat(self, request: ChatRequest) -> ChatResult:
        return ChatResult(messages=request.messages, metrics=None)

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        return EmbeddingResult(vectors=(), metrics=None)


__all__ = ["NullProvider"]
