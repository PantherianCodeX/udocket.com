# pyright: strict
"""Default AIClient implementation."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from packages.ai.api import (
    AIClient,
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
from packages.ai.errors import ProviderNotConfiguredError, RouteNotFoundError
from packages.ai.routing.registry import RouteBinding, RouteRegistry
from packages.ai.safety.egress import EgressPolicy
from packages.ai.safety.residency import AllowAllResidencyPolicy, ResidencyPolicy
from packages.ai.types import AgentTask
from packages.ai.types.identifiers import ModelName, ProviderName, RouteName

if TYPE_CHECKING:
    from collections.abc import Mapping

    from packages.ai.config import AISettings
    from packages.ai.providers.interfaces import ProviderAdapter


class DefaultAIClient(AIClient):
    """Router that delegates to registered ProviderAdapter instances."""

    def __init__(
        self,
        *,
        settings: AISettings,
        providers: Mapping[ProviderName, ProviderAdapter],
        residency_policy: ResidencyPolicy | None = None,
        egress_policy: EgressPolicy | None = None,
    ) -> None:
        self._settings: AISettings = settings
        self._providers: Mapping[ProviderName, ProviderAdapter] = providers
        self._residency_policy: ResidencyPolicy = residency_policy or AllowAllResidencyPolicy()
        allowed = egress_policy or EgressPolicy.from_list([str(name) for name in providers])
        self._egress_policy: EgressPolicy = allowed
        self._routes: RouteRegistry = self._build_registry(settings)

    def summarize(self, request: SummarizeRequest) -> SummarizeResult:
        adapter = self._resolve_adapter(AgentTask.SUMMARIZE)
        return adapter.summarize(request)

    def compose(self, request: ComposeRequest) -> ComposeResult:
        adapter = self._resolve_adapter(AgentTask.COMPOSE)
        return adapter.compose(request)

    def extract_timeline(
        self,
        request: TimelineExtractionRequest,
    ) -> TimelineExtractionResult:
        adapter = self._resolve_adapter(AgentTask.TIMELINE)
        return adapter.extract_timeline(request)

    def extract_entities(
        self,
        request: EntityExtractionRequest,
    ) -> EntityExtractionResult:
        adapter = self._resolve_adapter(AgentTask.ENTITIES)
        return adapter.extract_entities(request)

    def chat(self, request: ChatRequest) -> ChatResult:
        adapter = self._resolve_adapter(AgentTask.CHAT)
        return adapter.chat(request)

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        adapter = self._resolve_adapter(AgentTask.EMBED)
        return adapter.embed(request)

    # Internal helpers -------------------------------------------------

    def _build_registry(self, settings: AISettings) -> RouteRegistry:
        registry: dict[AgentTask, tuple[RouteBinding, ...]] = {}
        grouped: dict[AgentTask, list[RouteBinding]] = defaultdict(list)
        for route in settings.routes:
            grouped[route.task].append(
                RouteBinding(
                    task=route.task,
                    provider=route.provider,
                    model=route.model,
                    route_name=self._route_name(route.provider, route.model),
                ),
            )
        for task, entries in grouped.items():
            registry[task] = tuple(entries)
        return registry

    def _route_name(self, provider: ProviderName, model: ModelName) -> RouteName:
        return RouteName(f"{provider}:{model}")

    def _resolve_binding(self, task: AgentTask) -> RouteBinding:
        candidates = self._routes.get(task)
        if not candidates:
            raise RouteNotFoundError(task=task, provider=None)
        return candidates[0]

    def _resolve_adapter(self, task: AgentTask) -> ProviderAdapter:
        binding = self._resolve_binding(task)
        adapter = self._providers.get(binding.provider)
        if adapter is None:
            raise ProviderNotConfiguredError(task=task)
        self._residency_policy.assert_allowed(
            provider=adapter.name,
            region=adapter.region,
            task=task,
        )
        self._egress_policy.assert_allowed(adapter.name)
        return adapter


__all__ = ["DefaultAIClient"]
