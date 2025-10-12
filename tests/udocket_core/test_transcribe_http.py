# pyright: strict

from __future__ import annotations

import logging

from typing import Any, Dict, List

import pytest

from packages.udocket_core.agents.common.azure_speech import (
    AzureSpeechClient,
    AzureSpeechClientConfig,
    AzureSpeechError,
)


class _FakeResponse:
    def __init__(self, *, status_code: int = 200, json_payload: Dict[str, Any] | None = None, headers: Dict[str, str] | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._json = json_payload or {}
        self.headers = headers or {}
        self.text = text

    def json(self) -> Dict[str, Any]:  # pragma: no cover - simple helper
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeSession:
    def __init__(self, *, post_responses: List[_FakeResponse], get_responses: List[_FakeResponse]) -> None:
        self._post_responses = post_responses
        self._get_responses = get_responses
        self.calls: List[tuple[str, str]] = []

    def post(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append(("POST", url))
        return self._post_responses.pop(0)

    def get(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append(("GET", url))
        return self._get_responses.pop(0)


class _FakeManager:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session
        self.requests: List[str] = []

    def session_for(self, url: str) -> _FakeSession:
        self.requests.append(url)
        return self._session


def test_azure_speech_client_uses_session_manager() -> None:
    create_response = _FakeResponse(
        status_code=202,
        headers={"Location": "https://example.test/jobs/123"},
        json_payload={"self": "https://example.test/jobs/123"},
    )
    poll_response = _FakeResponse(
        status_code=200,
        json_payload={"status": "Succeeded", "recognizedPhrases": []},
    )
    files_response = _FakeResponse(
        status_code=200,
        json_payload={
            "values": [
                {
                    "kind": "Transcription",
                    "links": {"contentUrl": "https://example.test/jobs/123/transcript"},
                }
            ]
        },
    )
    transcript_response = _FakeResponse(
        status_code=200,
        json_payload={
            "recognizedPhrases": [],
            "combinedRecognizedPhrases": [
                {"display": "Hello World"},
            ],
        },
    )

    session = _FakeSession(
        post_responses=[create_response],
        get_responses=[poll_response, files_response, transcript_response],
    )
    manager = _FakeManager(session)
    client = AzureSpeechClient(
        AzureSpeechClientConfig(key="secret", region="canadacentral", session_manager=manager),
        logger=logging.getLogger("test.azure_speech"),
    )

    result = client.run_batch_transcription(
        audio_url="https://storage.test/audio.wav",
        locale="en-CA",
        diarization=False,
        display_name="Unit Test",
    )

    assert result.text == "Hello World"
    assert result.duration_s is None
    assert result.metadata["azure_transcription_url"] == "https://example.test/jobs/123"
    assert manager.requests[0].startswith("https://canadacentral")
    assert ("POST", manager.requests[0]) in session.calls
    assert len(session.calls) >= 4  # create + poll + files + transcript


class _RaisingSession:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def post(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls += 1
        return self.response

    def get(self, url: str, **kwargs: Any) -> _FakeResponse:
        raise RuntimeError('unexpected get')


class _FailureSession:
    def __init__(self) -> None:
        self.post_calls = 0
        self.get_calls = 0

    def post(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.post_calls += 1
        return _FakeResponse(status_code=202, headers={'Location': 'https://example.test/jobs/124'}, json_payload={'self': 'https://example.test/jobs/124'})

    def get(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.get_calls += 1
        if url.endswith('/files'):
            return _FakeResponse(status_code=200, json_payload={'values': []})
        return _FakeResponse(status_code=200, json_payload={'status': 'Failed', 'error': {'message': 'boom'}})


class _SingleSessionManager:
    def __init__(self, session: Any) -> None:
        self._session = session

    def session_for(self, url: str) -> Any:
        return self._session


class _FailureSessionManager:
    def __init__(self) -> None:
        self.session = _FailureSession()

    def session_for(self, url: str) -> Any:
        return self.session


def test_azure_speech_client_create_failure() -> None:
    session = _RaisingSession(_FakeResponse(status_code=400, text='bad'))
    client = AzureSpeechClient(
        AzureSpeechClientConfig(key='secret', region='canadacentral', session_manager=_SingleSessionManager(session)),
        logger=logging.getLogger('test.azure_speech'),
    )
    with pytest.raises(AzureSpeechError):
        client.run_batch_transcription(
            audio_url='https://storage.test/audio.wav',
            locale='en-CA',
            diarization=False,
            display_name='Unit Test',
        )
    assert session.calls == 1


def test_azure_speech_client_poll_failure() -> None:
    manager = _FailureSessionManager()
    client = AzureSpeechClient(
        AzureSpeechClientConfig(key='secret', region='canadacentral', session_manager=manager),
        logger=logging.getLogger('test.azure_speech'),
    )
    with pytest.raises(AzureSpeechError):
        client.run_batch_transcription(
            audio_url='https://storage.test/audio.wav',
            locale='en-CA',
            diarization=False,
            display_name='Unit Test',
        )
    assert manager.session.post_calls == 1
    assert manager.session.get_calls >= 1
