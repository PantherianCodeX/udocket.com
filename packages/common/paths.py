from __future__ import annotations

# pyright: strict

"""Common filesystem helpers for case-scoped storage."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CasePaths:
    """Resolved directories for a single case within tenant storage."""

    root: Path
    audio: Path
    transcript: Path
    analysis: Path
    ops: Path
    docs: Path

    def ensure(self) -> None:
        """Create the known subdirectories if they do not already exist."""

        for path in (self.audio, self.transcript, self.analysis, self.ops, self.docs):
            path.mkdir(parents=True, exist_ok=True)


def build_case_paths(root: Path) -> CasePaths:
    """Return the standard directory layout beneath ``root``."""

    base = root.resolve()
    return CasePaths(
        root=base,
        audio=base / "audio",
        transcript=base / "transcript",
        analysis=base / "analysis",
        ops=base / "ops",
        docs=base / "docs",
    )


__all__ = ["CasePaths", "build_case_paths"]
