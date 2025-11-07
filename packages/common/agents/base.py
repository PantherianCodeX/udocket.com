# pyright: strict

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AnalysisArtifact:
    kind: str
    path: Path
    checksum: str


@dataclass(slots=True)
class AnalysisResult:
    status: str
    artifacts: list[AnalysisArtifact]
    meta_path: Path
    audit_path: Path


__all__ = ["AnalysisArtifact", "AnalysisResult"]
