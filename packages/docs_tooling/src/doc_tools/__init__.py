"""Documentation tooling for uDocket engineering docs."""

from __future__ import annotations

import importlib
from types import ModuleType

__all__ = ["manage_docs", "paths", "pytest_runner"]


def __getattr__(name: str) -> ModuleType:  # pragma: no cover - thin wrapper
    if name not in __all__:
        raise AttributeError(f"module 'doc_tools' has no attribute {name!r}")
    return importlib.import_module(f".{name}", __name__)
