from __future__ import annotations

import importlib
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, cast, override

if TYPE_CHECKING:
    import pytest
else:
    pytest = importlib.import_module("pytest")

from packages.ai import CaseContext
from packages.ai.api import ChatMessage, ChatRequest, EmbeddingRequest
from packages.ai.errors import ProviderConfigurationError
from packages.ai.providers.azure_openai import AzureOpenAIAdapter
from packages.ai.providers.settings import AzureOpenAIConfig
from packages.ai.safety.egress import EgressPolicy
from packages.ai.safety.residency import AllowAllResidencyPolicy
from packages.ai.secret import SecretSource
from packages.ai.telemetry import ProviderCallMetrics
from packages.ai.types import AgentTask, Region
from packages.ai.types.identifiers import CaseID, ModelName, OrganizationID, ProviderName, RouteName

JSONPrimitive = str | int | float | bool | None
type JSONValue = JSONPrimitive | Mapping[str, JSONValue] | Sequence[JSONValue]
type JSONMapping = Mapping[str, JSONValue]


class DummySecretSource(SecretSource):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value

    @override
    def get(self, name: str) -> str | None:
        return self.value if name else None


class DummyResponse:
    def __init__(self, payload: JSONMapping) -> None:
        super().__init__()
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            msg = f"HTTP error {self.status_code}"
            raise RuntimeError(msg)

    def json(self) -> JSONMapping:
        return self._payload


def _base_config() -> AzureOpenAIConfig:
    return AzureOpenAIConfig(
        name=ProviderName("azure"),
        region=Region("primary"),
        allowed_regions=(),
        endpoint="https://example.azure.com",
        deployment="gpt-lite",
        api_key_env="AZURE_KEY",
    )


def _build_adapter(secret_value: str) -> AzureOpenAIAdapter:
    return AzureOpenAIAdapter(
        config=_base_config(),
        secret_source=DummySecretSource(secret_value),
        residency_policy=AllowAllResidencyPolicy(),
        egress_policy=EgressPolicy.from_list(["azure"]),
    )


DEFAULT_CREDENTIAL_VALUE = "test-token"
METRIC_TOTAL_TOKENS = 10
METRIC_PROMPT_TOKENS = 4


def _chat_payload() -> JSONMapping:
    return cast(
        "JSONMapping",
        {
            "choices": [
                {"message": {"content": "Hello"}},
            ],
            "usage": {
                "total_tokens": "10",
                "prompt_tokens": 4.0,
                "completion_tokens": "not-a-number",
            },
        },
    )


def _structured_payload() -> JSONMapping:
    return cast(
        "JSONMapping",
        {
            "choices": [
                {
                    "message": {
                        "content": [
                            {"type": "tool", "text": "structured"},
                        ],
                    },
                },
            ],
            "usage": {},
        },
    )


def _adapter_with_payload(
    monkeypatch: pytest.MonkeyPatch,
    payload: JSONMapping,
    *,
    secret_value: str = DEFAULT_CREDENTIAL_VALUE,
) -> AzureOpenAIAdapter:
    adapter = _build_adapter(secret_value)

    def _fake_post(
        url: str,
        *,
        headers: Mapping[str, str],
        data: str | bytes,
        timeout: int,
    ) -> DummyResponse:
        assert "deployments" in url
        assert "api-key" in headers
        _ = (data, timeout)
        return DummyResponse(payload)

    monkeypatch.setattr("packages.ai.providers.azure_openai.requests.post", _fake_post)
    return adapter


def test_chat_invocation_returns_message(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _adapter_with_payload(monkeypatch, _chat_payload())
    request = ChatRequest(
        context=CaseContext(org_id=OrganizationID("org"), case_id=CaseID("case")),
        messages=(ChatMessage(role="user", content="Hi"),),
    )
    result = adapter.chat(request)
    assert result.messages[-1].content == "Hello"
    assert isinstance(result.metrics, ProviderCallMetrics)
    assert result.metrics.total_tokens == METRIC_TOTAL_TOKENS
    assert result.metrics.prompt_tokens == METRIC_PROMPT_TOKENS
    assert result.metrics.completion_tokens is None


def test_chat_serializes_non_string_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter_with_payload(monkeypatch, _structured_payload())
    request = ChatRequest(
        context=CaseContext(org_id=OrganizationID("org"), case_id=CaseID("case")),
        messages=(ChatMessage(role="user", content="Hi"),),
    )
    result = adapter.chat(request)
    assert result.messages[-1].content == '[{"type": "tool", "text": "structured"}]'


def test_available_models() -> None:
    adapter = _build_adapter(DEFAULT_CREDENTIAL_VALUE)
    assert adapter.available_models(AgentTask.CHAT) == (ModelName("gpt-lite"),)
    assert adapter.available_models(AgentTask.GENERATE) == ()


def test_embed_not_implemented() -> None:
    adapter = _build_adapter(DEFAULT_CREDENTIAL_VALUE)
    with pytest.raises(NotImplementedError):
        _ = adapter.embed(
            EmbeddingRequest(
                context=CaseContext(org_id=OrganizationID("org"), case_id=CaseID("case")),
                inputs=("hello",),
            ),
        )


def test_describe_route_formats_identifier() -> None:
    adapter = _build_adapter(DEFAULT_CREDENTIAL_VALUE)
    route = adapter.describe_route(task=AgentTask.CHAT, model=ModelName("gpt-lite"))
    assert route == RouteName("azure:chat:gpt-lite")


def test_chat_missing_api_key() -> None:
    adapter = _build_adapter(secret_value="")
    request = ChatRequest(
        context=CaseContext(org_id=OrganizationID("org"), case_id=CaseID("case")),
        messages=(ChatMessage(role="user", content="Hi"),),
    )
    with pytest.raises(ProviderConfigurationError):
        _ = adapter.chat(request)
