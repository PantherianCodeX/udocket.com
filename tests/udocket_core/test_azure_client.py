from __future__ import annotations

import json
from typing import Any, Dict

import pytest

from packages.udocket_core.agents.common.azure_client import (
    AzureChatClient,
    AzureClientConfig,
)


class _FakeResponse:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload
        self.status_code = 200
        self.text = json.dumps(payload)
        self.headers: Dict[str, str] = {}

    def raise_for_status(self) -> None:  # pragma: no cover - parity with requests.Response
        return None

    def json(self) -> Dict[str, Any]:
        return self._payload

    def iter_lines(self, decode_unicode: bool = False):
        chunk = json.dumps(self._payload)
        line = f"data: {chunk}"
        done = "data: [DONE]"
        if decode_unicode:
            yield line
            yield done
        else:
            yield line.encode("utf-8")
            yield done.encode("utf-8")


class _FakeSession:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload
        self.calls: list[Dict[str, Any]] = []

    def post(
        self,
        url: str,
        *,
        params: Dict[str, Any] | None = None,
        headers: Dict[str, Any] | None = None,
        json: Any = None,
        stream: bool | None = None,
        timeout: Any = None,
    ) -> _FakeResponse:
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
        return _FakeResponse(self._payload)

    def close(self) -> None:
        return None


class _FakeSessionManager:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self.session = _FakeSession(payload)

    def session_for(self, endpoint: str) -> _FakeSession:
        return self.session

    def reset_session(self, endpoint: str) -> None:
        return None


def _client(monkeypatch: pytest.MonkeyPatch, payload: Dict[str, Any]) -> AzureChatClient:
    config = AzureClientConfig(
        endpoint="https://example.canadaeast.cognitiveservices.azure.com",  # allowed region
        key="test-key",
        deployment="gpt-4o-mini",
    )
    return AzureChatClient(config, session_manager=_FakeSessionManager(payload))


def test_chat_combines_fragmented_content(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "choices": [
            {
                "index": 0,
                "finish_reason": "length",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "{\n  \"issues\": ["},
                        {"type": "text", "text": "\"Item 1\", \"Item 2\"]\n}"},
                    ],
                },
            }
        ],
        "usage": {"input_tokens": 10, "output_tokens": 20},
    }

    client = _client(monkeypatch, payload)
    content, usage = client.chat(messages=[])

    assert json.loads(content) == {"issues": ["Item 1", "Item 2"]}
    assert usage["output_tokens"] == 20


def test_chat_prefers_structured_json_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_json",
                            "json": {"facts": ["alpha", "beta"]},
                        },
                        {"type": "text", "text": "irrelevant"},
                    ],
                },
            }
        ],
        "usage": {"input_tokens": 5, "output_tokens": 8},
    }

    client = _client(monkeypatch, payload)
    content, _ = client.chat(messages=[])

    assert json.loads(content) == {"facts": ["alpha", "beta"]}


def test_chat_reads_annotations_when_content_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": [],
                    "annotations": [
                        {
                            "type": "json_schema",
                            "output_json": {
                                "entities": [
                                    {
                                        "id": "E1",
                                        "name": "Alice",
                                        "type": "PERSON",
                                        "aliases": [],
                                    }
                                ],
                                "relations": [],
                            },
                        }
                    ],
                },
            }
        ],
        "usage": {"input_tokens": 12, "output_tokens": 18},
    }

    client = _client(monkeypatch, payload)
    content, usage = client.chat(messages=[])

    parsed = json.loads(content)
    assert parsed["entities"][0]["name"] == "Alice"
    assert usage["output_tokens"] == 18


def test_chat_reads_annotations_from_delta(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "choices": [
            {
                "index": 0,
                "finish_reason": "length",
                "message": {"role": "assistant", "content": ""},
                "delta": {
                    "annotations": [
                        {
                            "type": "json_schema",
                            "output_json": {"relations": [{"type": "ally"}]},
                        }
                    ]
                },
            }
        ],
        "usage": {"input_tokens": 7, "output_tokens": 9},
    }

    client = _client(monkeypatch, payload)
    content, usage = client.chat(messages=[])

    assert json.loads(content) == {"relations": [{"type": "ally"}]}
    assert usage["output_tokens"] == 9
