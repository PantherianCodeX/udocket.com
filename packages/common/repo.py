# pyright: strict

"""Repository-level path utilities shared across packages.

These helpers intentionally avoid importing application- or framework-specific
modules (e.g., Django settings) so they can be consumed from lightweight
tooling such as docs or ops scripts without dragging extra dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterable


def _infer_repo_root(anchor: Path | None = None) -> Path:
    """Infer the repository root using the known package layout."""

    base = (anchor or Path(__file__)).resolve()
    # `packages/common/repo.py` ⇒ parents[0] = packages/common,
    # parents[1] = packages, parents[2] = repo root.
    return base.parents[2]


REPO_ROOT: Final[Path] = _infer_repo_root()


@dataclass(frozen=True, slots=True)
class RepoPaths:
    """Typed view of common repository directories."""

    root: Path

    def join(self, *parts: str | Path) -> Path:
        """Return ``root`` joined with ``parts``."""

        path = self.root
        for part in parts:
            path = path / Path(part)
        return path


DEFAULT_REPO_PATHS: Final[RepoPaths] = RepoPaths(root=REPO_ROOT)


def ensure_dirs(paths: Iterable[Path]) -> None:
    """Create directories if they do not exist."""

    for entry in paths:
        entry.mkdir(parents=True, exist_ok=True)


__all__ = ["DEFAULT_REPO_PATHS", "REPO_ROOT", "RepoPaths", "ensure_dirs"]
