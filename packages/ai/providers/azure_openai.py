# pyright: strict

"""Azure OpenAI provider adapter."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import requests

from packages.ai.api import (
    ChatMessage,
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
from packages.ai.errors import ProviderConfigurationError
from packages.ai.providers.interfaces import ProviderAdapter
from packages.ai.types import AgentTask, ProviderCallMetrics, Region
from packages.ai.types.identifiers import ModelName, ProviderName, RouteName

if TYPE_CHECKING:
    from packages.ai.providers.settings import AzureOpenAIConfig
    from packages.ai.safety.egress import EgressPolicy
    from packages.ai.safety.residency import ResidencyPolicy
    from packages.ai.secret import SecretSource


def _coerce_int(value: object) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            try:
                return int(stripped)
            except ValueError:
                return None
    return None


@dataclass(slots=True)
class AzureOpenAIAdapter(ProviderAdapter):
    """Adapter that proxies Azure OpenAI deployments."""

    config: AzureOpenAIConfig
    secret_source: SecretSource
    residency_policy: ResidencyPolicy
    egress_policy: EgressPolicy

    @property
    def name(self) -> ProviderName:
        return self.config.name

    @property
    def region(self) -> Region:
        return self.config.region

    @property
    def supported_tasks(self) -> tuple[AgentTask, ...]:
        return (
            AgentTask.CHAT,
            AgentTask.EMBED,
        )

    def available_models(self, task: AgentTask) -> tuple[ModelName, ...]:
        if task in self.supported_tasks:
            return (ModelName(self.config.deployment),)
        return ()

    def summarize(
        self,
        request: SummarizeRequest,
    ) -> SummarizeResult:  # pragma: no cover - not wired yet
        message = "Summarize not wired to Azure adapter yet"
        raise NotImplementedError(message)

    def compose(self, request: ComposeRequest) -> ComposeResult:  # pragma: no cover - not wired yet
        message = "Compose not wired to Azure adapter yet"
        raise NotImplementedError(message)

    def extract_timeline(
        self,
        request: TimelineExtractionRequest,
    ) -> TimelineExtractionResult:  # pragma: no cover
        message = "Timeline extraction not wired to Azure adapter yet"
        raise NotImplementedError(message)

    def extract_entities(
        self,
        request: EntityExtractionRequest,
    ) -> EntityExtractionResult:  # pragma: no cover
        message = "Entity extraction not wired to Azure adapter yet"
        raise NotImplementedError(message)

    def chat(self, request: ChatRequest) -> ChatResult:
        payload = self._invoke_chat(request)
        return ChatResult(messages=payload.messages, metrics=payload.metrics)

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        message = "Embedding not implemented for Azure adapter"
        raise NotImplementedError(message)

    def describe_route(self, *, task: AgentTask, model: ModelName) -> RouteName | None:
        return RouteName(f"{self.name}:{task.value}:{model}")

    # Internal helpers -------------------------------------------------

    @dataclass(slots=True)
    class _ChatPayload:
        messages: tuple[ChatMessage, ...]
        metrics: ProviderCallMetrics

    def _invoke_chat(self, request: ChatRequest) -> _ChatPayload:
        api_key = self.secret_source.get(self.config.api_key_env)
        if not api_key:
            raise ProviderConfigurationError(
                provider=self.name,
                detail=f"API key missing for {self.config.api_key_env}",
            )
        self.residency_policy.assert_allowed(
            provider=self.name,
            region=self.region,
            task=AgentTask.CHAT,
            org_id=request.context.org_id if request.context else None,
        )
        self.egress_policy.assert_allowed(self.name)
        url = (
            f"{self.config.endpoint.rstrip('/')}/openai/deployments/"
            f"{self.config.deployment}/chat/completions?api-version=2024-02-15-preview"
        )
        messages_payload: list[dict[str, str]] = [
            {"role": msg.role, "content": msg.content} for msg in request.messages
        ]
        payload = {"messages": messages_payload}
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "api-key": api_key,
            },
            data=json.dumps(payload),
            timeout=120,
        )
        response.raise_for_status()
        data = cast("dict[str, object]", response.json())
        choices = cast("list[object]", data.get("choices") or [])
        content = ""
        if choices:
            first = cast("dict[str, object]", choices[0])
            message = cast("dict[str, object]", first.get("message") or {})
            raw_content = message.get("content")
            if isinstance(raw_content, str):
                content = raw_content
            else:
                content = json.dumps(raw_content, ensure_ascii=False)
        usage_payload = cast("dict[str, object]", data.get("usage") or {})
        metrics = ProviderCallMetrics(
            total_tokens=_coerce_int(usage_payload.get("total_tokens")),
            prompt_tokens=_coerce_int(usage_payload.get("prompt_tokens")),
            completion_tokens=_coerce_int(usage_payload.get("completion_tokens")),
        )
        assistant_message = ChatMessage(role="assistant", content=str(content))
        return AzureOpenAIAdapter._ChatPayload(
            messages=(*request.messages, assistant_message),
            metrics=metrics,
        )
