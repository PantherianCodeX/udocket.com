from __future__ import annotations

from packages.udocket_core.agents.analyze.stages.entity_stage import (
    _assign_entity_defaults,
    _assign_relation_defaults,
)
from packages.udocket_core.agents.analyze.stages.timeline_stage import _normalize_event


def test_normalize_event_preserves_uuid():
    payload = {
        "id": "event-1",
        "uuid": "seed-uuid-1",
        "text": "Hearing opened",
        "ts_start": 0,
        "ts_end": None,
        "speaker": "SPK_1",
        "labels": ["opening"],
    }

    normalized = _normalize_event(payload)
    assert normalized is not None
    assert normalized["uuid"] == "seed-uuid-1"
    assert normalized["id"] == "event-1"


def test_assign_entity_defaults_preserves_uuid():
    entity = {
        "id": "entity-1",
        "uuid": "entity-uuid-1",
        "name": "Alex Client",
        "type": "PERSON",
        "aliases": ["Mr. Client"],
        "mentions": [{"ts": 1.2, "text": "Alex Client"}],
    }

    normalized = _assign_entity_defaults(entity)
    assert normalized["uuid"] == "entity-uuid-1"
    assert normalized["id"] == "entity-1"


def test_assign_relation_defaults_preserves_uuid():
    relation = {
        "id": "rel-1",
        "uuid": "relation-uuid-1",
        "type": "REPRESENTS",
        "source": "entity-1",
        "target": "entity-2",
        "evidence": [{"ts": 10.0, "text": "Representation noted"}],
    }

    normalized = _assign_relation_defaults(relation)
    assert normalized["uuid"] == "relation-uuid-1"
    assert normalized["id"] == "rel-1"
