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

    def raise_for_status(self) -> None:  # pragma: no cover - parity with requests.Response
        return None

    def json(self) -> Dict[str, Any]:
        return self._payload


def _client(monkeypatch: pytest.MonkeyPatch, payload: Dict[str, Any]) -> AzureChatClient:
    def _fake_post(*args: Any, **kwargs: Any) -> _FakeResponse:
        return _FakeResponse(payload)

    from packages.udocket_core.agents.common import azure_client

    monkeypatch.setattr(azure_client.requests, "post", _fake_post)

    config = AzureClientConfig(
        endpoint="https://example.canadaeast.cognitiveservices.azure.com",  # allowed region
        key="test-key",
        deployment="gpt-4o-mini",
    )
    return AzureChatClient(config)


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
