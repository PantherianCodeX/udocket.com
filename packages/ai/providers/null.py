# pyright: strict

"""Deterministic no-op provider used in tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import override

from packages.ai.api import (
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
from packages.ai.types import AgentTask, Region
from packages.ai.types.identifiers import ModelName, ProviderName, RouteName

from .interfaces import ProviderAdapter


@dataclass(slots=True)
class NullProvider(ProviderAdapter):
    """Provider that returns empty payloads for deterministic tests."""

    _name: ProviderName = field(default_factory=lambda: ProviderName("null-provider"))
    _region: Region = field(default_factory=lambda: Region("test-region"))

    @property
    @override
    def name(self) -> ProviderName:
        return self._name

    @property
    @override
    def region(self) -> Region:
        return self._region

    @property
    @override
    def supported_tasks(self) -> tuple[AgentTask, ...]:
        return tuple(AgentTask)

    @override
    def available_models(self, task: AgentTask) -> tuple[ModelName, ...]:
        _ = task
        return (ModelName("null-model"),)

    @override
    def summarize(self, request: SummarizeRequest) -> SummarizeResult:
        _ = request
        return SummarizeResult(summary_text="", metrics=None)

    @override
    def compose(self, request: ComposeRequest) -> ComposeResult:
        _ = request
        return ComposeResult()

    @override
    def extract_timeline(
        self,
        request: TimelineExtractionRequest,
    ) -> TimelineExtractionResult:
        _ = request
        return TimelineExtractionResult(events=(), metrics=None)

    @override
    def extract_entities(
        self,
        request: EntityExtractionRequest,
    ) -> EntityExtractionResult:
        _ = request
        return EntityExtractionResult(entities=(), metrics=None)

    @override
    def describe_route(self, *, task: AgentTask, model: ModelName) -> RouteName | None:
        return RouteName(f"{task.value}:{model}")

    @override
    def chat(self, request: ChatRequest) -> ChatResult:
        return ChatResult(messages=request.messages, metrics=None)

    @override
    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        _ = request
        return EmbeddingResult(vectors=(), metrics=None)


__all__ = ["NullProvider"]
