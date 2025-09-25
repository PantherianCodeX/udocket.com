from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .io import AnalysisArtifact


@dataclass
class AnalysisResult:
    status: str
    artifacts: List[AnalysisArtifact]
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


__all__ = ["AnalysisResult", "AnalysisAgent"]
