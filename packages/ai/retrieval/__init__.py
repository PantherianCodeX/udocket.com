# pyright: strict

"""Retrieval interface definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(slots=True, frozen=True)
class RetrievalQuery:
    """Inputs provided to retrieval clients."""

    text: str
    top_k: int = 5


@dataclass(slots=True, frozen=True)
class RetrievalDocument:
    """Result entry returned by retrieval clients."""

    doc_id: str
    text: str
    score: float


@runtime_checkable
class RetrievalClient(Protocol):
    """Protocol for semantic/vector retrieval providers."""

    def search(self, query: RetrievalQuery) -> tuple[RetrievalDocument, ...]: ...


__all__ = ["RetrievalClient", "RetrievalDocument", "RetrievalQuery"]
