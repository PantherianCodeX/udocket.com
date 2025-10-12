# pyright: strict

from __future__ import annotations

import logging

import pytest

from packages.udocket_core.agents.common.llm_health import ensure_llm_client_health


class _HealthyClient:
    def __init__(self) -> None:
        self.invocations = 0

    def health_check(self, *, force: bool = False) -> None:  # pragma: no cover - signature match
        self.invocations += 1


class _FailingClient:
    def health_check(self, *, force: bool = False) -> None:  # pragma: no cover - signature match
        raise RuntimeError("boom")


def _raise_error(message: str) -> Exception:
    return RuntimeError(message)


def test_ensure_llm_client_health_success() -> None:
    client = _HealthyClient()
    ensure_llm_client_health(
        client,
        stage="unit.test",
        provider="azure",
        model="test-model",
        logger=logging.getLogger("test.llm"),
        raise_error=_raise_error,
    )
    assert client.invocations == 1


def test_ensure_llm_client_health_failure() -> None:
    client = _FailingClient()
    with pytest.raises(RuntimeError, match="Health check failed: boom"):
        ensure_llm_client_health(
            client,
            stage="unit.test",
            provider="azure",
            model="test-model",
            logger=logging.getLogger("test.llm"),
            raise_error=_raise_error,
        )


def test_ensure_llm_client_health_ignored_for_non_supporting_client() -> None:
    class _PlainClient:
        pass

    plain_client = _PlainClient()
    # Should not raise because the client lacks health-check support.
    ensure_llm_client_health(
        plain_client,
        stage="unit.test",
        provider="azure",
        model="test-model",
        logger=logging.getLogger("test.llm"),
        raise_error=_raise_error,
    )

