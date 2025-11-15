from __future__ import annotations

from uuid import uuid4

from packages.ai.telemetry.config import record_langfuse_session


def test_langfuse_disconnect_recorded() -> None:
    evidence = record_langfuse_session(uuid4(), disconnect_event=True)
    assert evidence.disconnect_event is True
