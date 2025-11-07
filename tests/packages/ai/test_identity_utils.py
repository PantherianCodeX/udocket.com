from __future__ import annotations

from packages.ai.utils.identity import NAMESPACE_AI, deterministic_uuid


def test_deterministic_uuid_stable() -> None:
    first = deterministic_uuid(namespace="summary", content="case-123")
    second = deterministic_uuid(namespace="summary", content="case-123")
    assert first == second


def test_deterministic_uuid_namespace_variation() -> None:
    a = deterministic_uuid(namespace="summary", content="case-123")
    b = deterministic_uuid(namespace="compose", content="case-123")
    assert a != b
    assert NAMESPACE_AI.version == 5
