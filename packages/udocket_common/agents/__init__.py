from __future__ import annotations

# pyright: strict

"""Shared agent-facing dataclasses and protocols."""

from .results import RegionLiteral, TranscriptionResult
from .base import AnalysisArtifact, AnalysisResult

__all__ = [
    "TranscriptionResult",
    "RegionLiteral",
    "AnalysisArtifact",
    "AnalysisResult",
]
