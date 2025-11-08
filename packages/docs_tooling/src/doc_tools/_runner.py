"""Minimal command runner for doc_tools to avoid re-import warnings."""

from __future__ import annotations

import runpy
from importlib import import_module


def run_module(module: str) -> int:
    mod = import_module(module)
    if hasattr(mod, "main"):
        result = mod.main()
        return int(result) if isinstance(result, int) else 0
    runpy.run_module(module, run_name="__main__")
    return 0


def run_manage_docs(argv: list[str]) -> int:
    mod = import_module("doc_tools.manage_docs")
    return mod.main(argv)
