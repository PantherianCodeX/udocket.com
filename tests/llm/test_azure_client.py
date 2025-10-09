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


class _FakeResponse:
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


class _FakeSession:
    def __init__(self, *, raise_transport: bool = False) -> None:
        self.raise_transport = raise_transport
        self.calls: list[Dict[str, Any]] = []
        self.response: _FakeResponse = _FakeResponse()

    def post(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
        json: object | None = None,
        timeout: int | float | None = None,
    ) -> _FakeResponse:
        self.calls.append(
            {
                "url": url,
                "params": params,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        if self.raise_transport:
            raise _FakeRequestsModule.exceptions.RequestException("transport down")
        return self.response


class _FakeSessionManager:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    def session_for(self, endpoint: str) -> _FakeSession:
        return self._session


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
    fake_session = _FakeSession()
    client = AzureChatClient(cfg, session_manager=_FakeSessionManager(fake_session))
    content, usage = client.chat(messages=[{"role": "user", "content": "hi"}])
    assert content == "ok"
    assert usage["total_tokens"] == 2
    assert fake_session.calls, "expected API call to be recorded"


def test_azure_transport_error_raises_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = AzureClientConfig(
        endpoint="https://canadacentral.api.cognitive.microsoft.com",
        key="secret",
        deployment="deploy",
        allow_non_ca_region=False,
    )
    fake_requests = _FakeRequestsModule()
    monkeypatch.setattr(azure_client, "requests", fake_requests)
    fake_session = _FakeSession(raise_transport=True)
    client = AzureChatClient(cfg, session_manager=_FakeSessionManager(fake_session))
    with pytest.raises(RuntimeError, match="transport error"):
        client.chat(messages=[{"role": "user", "content": "hi"}])


def test_azure_health_check(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = AzureClientConfig(
        endpoint="https://canadacentral.api.cognitive.microsoft.com",
        key="secret",
        deployment="deploy",
        allow_non_ca_region=False,
        health_check_cache_ttl=999,
    )
    fake_requests = _FakeRequestsModule()
    monkeypatch.setattr(azure_client, "requests", fake_requests)
    fake_session = _FakeSession()
    client = AzureChatClient(cfg, session_manager=_FakeSessionManager(fake_session))
    client.health_check()
    first_count = len(fake_session.calls)
    assert first_count == 1
    client.health_check()
    assert len(fake_session.calls) == first_count  # cached
    client.health_check(force=True)
    assert len(fake_session.calls) == first_count + 1
