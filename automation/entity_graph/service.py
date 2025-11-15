"""Entity Relationship Graph builder for AI refactor runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence
from uuid import UUID

_BASE_PATH = Path("storage/ops/ai-refactor/graphs")


@dataclass(frozen=True)
class EntityNode:
    node_id: UUID
    label: str
    entity_type: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class RelationshipEdge:
    source_id: UUID
    target_id: UUID
    relationship: str
    confidence: float
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class EntityGraph:
    run_id: UUID
    generated_at: str
    nodes: tuple[EntityNode, ...]
    edges: tuple[RelationshipEdge, ...]
    provenance_refs: tuple[str, ...]
    confidence: float


def _ensure_base() -> None:
    _BASE_PATH.mkdir(parents=True, exist_ok=True)


def write_graph(
    run_id: UUID,
    nodes: Sequence[EntityNode],
    edges: Sequence[RelationshipEdge],
    provenance_refs: Sequence[str],
    confidence: float,
) -> Path:
    _ensure_base()
    payload = {
        "run_id": str(run_id),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "nodes": [asdict(node) for node in nodes],
        "edges": [asdict(edge) for edge in edges],
        "provenance_refs": list(provenance_refs),
        "confidence": confidence,
    }
    path = _BASE_PATH / f"graph_{run_id}.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"))
    return path


def load_graph(path: Path) -> EntityGraph:
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return EntityGraph(
        run_id=UUID(raw["run_id"]),
        generated_at=raw["generated_at"],
        nodes=tuple(EntityNode(**node) for node in raw.get("nodes", [])),
        edges=tuple(RelationshipEdge(**edge) for edge in raw.get("edges", [])),
        provenance_refs=tuple(raw.get("provenance_refs", [])),
        confidence=float(raw.get("confidence", 0.0)),
    )
