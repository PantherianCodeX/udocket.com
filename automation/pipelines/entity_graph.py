"""Helpers that expose entity graph snapshots to automation pipelines."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from uuid import UUID

from automation.entity_graph.service import EntityGraph, load_graph

_GRAPH_DIR = Path("storage/ops/ai-refactor/graphs")


def latest_graph_path() -> Optional[Path]:
    files = sorted(_GRAPH_DIR.glob("graph_*.json"))
    if not files:
        return None
    return files[-1]


def latest_graph() -> Optional[EntityGraph]:
    path = latest_graph_path()
    if not path:
        return None
    return load_graph(path)


def graph_context(run_id: UUID) -> Optional[EntityGraph]:
    path = _GRAPH_DIR / f"graph_{run_id}.json"
    if not path.exists():
        return None
    return load_graph(path)
