from __future__ import annotations

# pyright: strict

from dataclasses import dataclass
from pathlib import Path

from .io import AnalysisArtifact


@dataclass(frozen=True)
class AnalysisResult:
    status: str
    artifacts: list[AnalysisArtifact]
    meta_path: Path
    audit_path: Path


class AnalysisAgent:
    """Minimal interface for future analysis agents."""

    def run(  # pragma: no cover - interface definition
        self,
        *,
        case_id: str,
        case_dir: Path,
        job_id: str,
        **kwargs: object,
    ) -> AnalysisResult:
        raise NotImplementedError


__all__: list[str] = ["AnalysisResult", "AnalysisAgent"]
