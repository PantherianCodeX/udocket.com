# pyright: strict

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping

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

        class ConnectionError(RequestException):
            ...

        class Timeout(RequestException):
            ...


@pytest.fixture(autouse=True)
def reset_fallback_state() -> None:
    azure_client._reset_fallback_state()
    yield
    azure_client._reset_fallback_state()


class _FakeStreamingResponse:
    def __init__(
        self,
        chunks: list[Mapping[str, object]],
        *,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        text: str = "",
    ) -> None:
        self._chunks = chunks
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise _FakeRequestsModule.exceptions.HTTPError(self)

    def iter_lines(self, decode_unicode: bool = False):
        for chunk in self._chunks:
            payload = json.dumps(chunk)
            line = f"data: {payload}"
            if decode_unicode:
                yield line
            else:
                yield line.encode("utf-8")
        done = "data: [DONE]"
        if decode_unicode:
            yield done
        else:
            yield done.encode("utf-8")


def _make_streaming_response(
    *,
    content: str = "ok",
    usage: Mapping[str, int] | None = None,
) -> _FakeStreamingResponse:
    chunks: list[Mapping[str, object]] = [
        {"choices": [{"index": 0, "delta": {"role": "assistant"}}]},
        {"choices": [{"index": 0, "delta": {"content": content}}]},
    ]
    if usage is not None:
        chunks.append({"usage": dict(usage)})
    return _FakeStreamingResponse(chunks=chunks)


class _FakeSession:
    def __init__(
        self,
        *,
        raise_transport: bool = False,
        response: _FakeStreamingResponse | None = None,
        transport_exception: type[Exception] | None = None,
    ) -> None:
        self.raise_transport = raise_transport
        self.transport_exception = transport_exception or _FakeRequestsModule.exceptions.ConnectionError
        self.calls: list[Dict[str, Any]] = []
        self.response: _FakeStreamingResponse = response or _make_streaming_response(
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
        )
        self.closed = False

    def post(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
        json: object | None = None,
        stream: bool | None = None,
        timeout: int | float | tuple[float, float] | None = None,
    ) -> _FakeStreamingResponse:
        self.calls.append(
            {
                "url": url,
                "params": params,
                "headers": headers,
                "json": json,
                "stream": stream,
                "timeout": timeout,
            }
        )
        if self.raise_transport:
            raise self.transport_exception("transport down")
        return self.response

    def close(self) -> None:
        self.closed = True


class _FakeSessionManager:
    def __init__(self, session: Any) -> None:
        self._session = session
        self.reset_calls: list[str] = []

    def session_for(self, endpoint: str) -> Any:
        return self._session

    def reset_session(self, endpoint: str) -> None:
        self.reset_calls.append(endpoint)
        close = getattr(self._session, "close", None)
        if callable(close):
            close()


class _SequenceSession:
    def __init__(self, responses: List[_FakeStreamingResponse]) -> None:
        self._responses = responses
        self.calls: list[Dict[str, Any]] = []
        self.closed = False

    def post(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
        json: object | None = None,
        stream: bool | None = None,
        timeout: int | float | tuple[float, float] | None = None,
    ) -> _FakeStreamingResponse:
        self.calls.append(
            {
                "url": url,
                "params": params,
                "headers": headers,
                "json": json,
                "stream": stream,
                "timeout": timeout,
            }
        )
        response = self._responses.pop(0)
        return response

    def close(self) -> None:
        self.closed = True


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
    fake_session = _FakeSession(
        raise_transport=True,
        transport_exception=_FakeRequestsModule.exceptions.ConnectionError,
    )
    manager = _FakeSessionManager(fake_session)
    client = AzureChatClient(cfg, session_manager=manager)
    with pytest.raises(RuntimeError, match="request failed after retries"):
        client.chat(messages=[{"role": "user", "content": "hi"}])
    assert manager.reset_calls == ["https://canadacentral.api.cognitive.microsoft.com"]
    assert fake_session.closed


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
    payload = fake_session.calls[0]["json"]
    assert isinstance(payload, dict)
    messages = payload.get("messages")
    assert isinstance(messages, list) and len(messages) == 2
    assert messages[1]["content"] == "Reply with the word OK."
    assert payload.get("max_completion_tokens") == 256
    assert payload.get("stream") is True
    assert fake_session.calls[0]["stream"] is True
    client.health_check()
    assert len(fake_session.calls) == first_count  # cached
    client.health_check(force=True)
    assert len(fake_session.calls) == first_count + 1


def test_azure_temperature_fallback_persists(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = AzureClientConfig(
        endpoint="https://canadacentral.api.cognitive.microsoft.com",
        key="secret",
        deployment="deploy",
        allow_non_ca_region=False,
    )
    fake_requests = _FakeRequestsModule()
    monkeypatch.setattr(azure_client, "requests", fake_requests)

    error_text = (
        "Unsupported value: 'temperature' does not support 0.0 with this model. "
        "Only the default (1) value is supported."
    )
    error_response = _FakeStreamingResponse(chunks=[], status_code=400, text=error_text)
    success_response_one = _make_streaming_response(content="fallback-ok")
    session_first = _SequenceSession([error_response, success_response_one])
    manager_first = _FakeSessionManager(session_first)
    client = AzureChatClient(cfg, session_manager=manager_first)

    content, _ = client.chat(messages=[{"role": "user", "content": "hi"}], temperature=0.0)
    assert content == "fallback-ok"
    assert len(session_first.calls) == 2
    assert session_first.calls[0]["json"]["temperature"] == 0.0
    assert session_first.calls[1]["json"]["temperature"] == 1.0

    success_response_two = _make_streaming_response(content="fallback-ok-again")
    session_second = _FakeSession(response=success_response_two)
    manager_second = _FakeSessionManager(session_second)
    client_two = AzureChatClient(cfg, session_manager=manager_second)
    content_two, _ = client_two.chat(messages=[{"role": "user", "content": "again"}], temperature=0.4)
    assert content_two == "fallback-ok-again"
    assert len(session_second.calls) == 1
    assert session_second.calls[0]["json"]["temperature"] == 1.0


def test_azure_max_output_fallback_persists(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = AzureClientConfig(
        endpoint="https://canadacentral.api.cognitive.microsoft.com",
        key="secret",
        deployment="deploy",
        allow_non_ca_region=False,
    )
    fake_requests = _FakeRequestsModule()
    monkeypatch.setattr(azure_client, "requests", fake_requests)

    error_response = _FakeStreamingResponse(
        chunks=[],
        status_code=400,
        text="Parameter max_output_tokens is not supported for this deployment.",
    )
    success_response_one = _make_streaming_response(content="max-ok")
    session_first = _SequenceSession([error_response, success_response_one])
    manager_first = _FakeSessionManager(session_first)
    client = AzureChatClient(cfg, session_manager=manager_first)

    first_content, _ = client.chat(messages=[{"role": "user", "content": "hi"}], max_tokens=128)
    assert first_content == "max-ok"
    assert len(session_first.calls) == 2
    assert session_first.calls[0]["json"]["max_output_tokens"] == 128
    assert "max_output_tokens" not in session_first.calls[1]["json"]

    success_response_two = _make_streaming_response(content="max-ok-again")
    session_second = _FakeSession(response=success_response_two)
    manager_second = _FakeSessionManager(session_second)
    client_two = AzureChatClient(cfg, session_manager=manager_second)
    second_content, _ = client_two.chat(messages=[{"role": "user", "content": "again"}], max_tokens=64)
    assert second_content == "max-ok-again"
    assert len(session_second.calls) == 1
    assert "max_output_tokens" not in session_second.calls[0]["json"]
    assert session_second.calls[0]["json"]["max_completion_tokens"] == 64


def test_timeout_tuple_passed(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = AzureClientConfig(
        endpoint="https://canadacentral.api.cognitive.microsoft.com",
        key="secret",
        deployment="deploy",
        allow_non_ca_region=False,
        connect_timeout=7,
        read_timeout=333,
    )
    fake_requests = _FakeRequestsModule()
    monkeypatch.setattr(azure_client, "requests", fake_requests)
    session = _FakeSession()
    client = AzureChatClient(cfg, session_manager=_FakeSessionManager(session))
    client.chat(messages=[{"role": "user", "content": "hi"}])
    assert session.calls, "expected API call"
    timeout = session.calls[0]["timeout"]
    assert isinstance(timeout, tuple) and timeout == (7.0, 333.0)
    assert session.calls[0]["stream"] is True
