# pyright: strict

from __future__ import annotations

from typing import Any, Dict, Mapping

import pytest

from packages.udocket_core.agents.common import azure_client
from packages.udocket_core.agents.common.azure_client import AzureChatClient, AzureClientConfig


class _FakeRequestsModule:
    class exceptions:  # type: ignore[too-few-public-methods]
        class HTTPError(Exception):
            def __init__(self, response: object | None = None) -> None:
                super().__init__("http error")
                self.response = response

        class RequestException(Exception):
            ...

    def __init__(self, *, should_raise_transport: bool = False) -> None:
        self.should_raise_transport = should_raise_transport
        self.last_payload: Dict[str, Any] | None = None

    def post(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
        json: object | None = None,
        timeout: int | float | None = None,
    ):
        if self.should_raise_transport:
            raise self.exceptions.RequestException("transport down")
        self.last_payload = {"url": url, "params": params, "headers": headers, "json": json, "timeout": timeout}

        class _Response:
            status_code = 200
            text = "{}"
            headers: Mapping[str, str] = {}

            def raise_for_status(self) -> None:
                return None

            def json(self) -> object:
                return {
                    "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }

        return _Response()


def test_azure_config_disallows_non_canadian_endpoint() -> None:
    cfg = AzureClientConfig(
        endpoint="https://example-eastus.azure.com",
        key="secret",
        deployment="deploy",
        allow_non_ca_region=False,
    )
    with pytest.raises(ValueError):
        cfg.validate()


def test_azure_config_allows_override(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = AzureClientConfig(
        endpoint="https://example-eastus.azure.com",
        key="secret",
        deployment="deploy",
        allow_non_ca_region=True,
    )
    fake_requests = _FakeRequestsModule()
    monkeypatch.setattr(azure_client, "requests", fake_requests)
    client = AzureChatClient(cfg)
    content, usage = client.chat(messages=[{"role": "user", "content": "hi"}])
    assert content == "ok"
    assert usage["total_tokens"] == 2


def test_azure_transport_error_raises_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = AzureClientConfig(
        endpoint="https://canadacentral.api.cognitive.microsoft.com",
        key="secret",
        deployment="deploy",
        allow_non_ca_region=False,
    )
    fake_requests = _FakeRequestsModule(should_raise_transport=True)
    monkeypatch.setattr(azure_client, "requests", fake_requests)
    client = AzureChatClient(cfg)
    with pytest.raises(RuntimeError, match="transport error"):
        client.chat(messages=[{"role": "user", "content": "hi"}])
