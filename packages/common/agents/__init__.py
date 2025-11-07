# pyright: strict

"""Shared agent-facing dataclasses and protocols."""

from __future__ import annotations

from .base import AnalysisArtifact, AnalysisResult
from .results import RegionLiteral, TranscriptionResult

__all__ = [
    "TranscriptionResult",
    "RegionLiteral",
    "AnalysisArtifact",
    "AnalysisResult",
]
