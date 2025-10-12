# pyright: strict

from __future__ import annotations

import logging

import pytest

from packages.udocket_core.agents.common.azure_speech import (
    AzureSpeechHealthConfig,
    ensure_azure_speech_health,
)


class _FakeResponse:
    def __init__(self, status_code: int = 200, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


class _FakeSession:
    def __init__(self, *, response: _FakeResponse, should_raise: bool = False) -> None:
        self.response = response
        self.should_raise = should_raise
        self.calls = 0

    def post(self, *args, **kwargs):  # noqa: D401 - test double
        self.calls += 1
        if self.should_raise:
            raise RuntimeError("network down")
        return self.response


class _FakeSessionManager:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    def session_for(self, _endpoint: str) -> _FakeSession:
        return self._session


def _raise(message: str) -> Exception:
    return RuntimeError(message)


def _config(session: _FakeSession) -> AzureSpeechHealthConfig:
    return AzureSpeechHealthConfig(cache_ttl_s=999, timeout_s=5.0, session_manager=_FakeSessionManager(session))


def test_azure_speech_health_success_cached() -> None:
    session = _FakeSession(response=_FakeResponse(status_code=200))
    cfg = _config(session)

    ensure_azure_speech_health(
        key="secret",
        region="canadacentral",
        logger=logging.getLogger("test.speech"),
        raise_error=_raise,
        config=cfg,
        force=False,
    )
    assert session.calls == 1

    ensure_azure_speech_health(
        key="secret",
        region="canadacentral",
        logger=logging.getLogger("test.speech"),
        raise_error=_raise,
        config=cfg,
        force=False,
    )
    assert session.calls == 1, "health check should use cache"


def test_azure_speech_health_failure_status() -> None:
    session = _FakeSession(response=_FakeResponse(status_code=401, text="unauthorized"))
    cfg = _config(session)
    with pytest.raises(RuntimeError, match="credential test failed"):
        ensure_azure_speech_health(
            key="secret",
            region="canadaeast",
            logger=logging.getLogger("test.speech"),
            raise_error=_raise,
            config=cfg,
        )
    assert session.calls == 1


def test_azure_speech_health_transport_failure() -> None:
    session = _FakeSession(response=_FakeResponse(), should_raise=True)
    cfg = _config(session)
    with pytest.raises(RuntimeError, match="transport error"):
        ensure_azure_speech_health(
            key="secret",
            region="canadacentral",
            logger=logging.getLogger("test.speech"),
            raise_error=_raise,
            config=cfg,
            force=True,
        )
    assert session.calls == 1
