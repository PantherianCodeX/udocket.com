"""Compatibility package that exposes legacy `docs.*` modules.

Historically the documentation tooling lived under a top-level `docs/` package.
The content now resides in `packages/udocket_docs`, but a number of scripts and
third-party integrations still import modules such as `docs.tools.manage_docs`.
This compatibility layer keeps those imports working while the source of truth
lives alongside the new docs package.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_TOOLS_MODULE = "packages.udocket_docs.tools"

if str(_REPO_ROOT) not in sys.path:
    sys.path.append(str(_REPO_ROOT))

_tools = importlib.import_module(_TOOLS_MODULE)
sys.modules.setdefault(__name__ + ".tools", _tools)

__all__ = ["tools"]
