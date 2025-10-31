#!/usr/bin/env python3
"""Synchronise documentation static assets for MkDocs consumption."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "docs" / "src"
ASSET_TARGET = SRC_ROOT / "_assets"
MERMAID_SOURCE = ROOT / "docs" / "build" / "mermaid"
MERMAID_TARGET = ASSET_TARGET / "mermaid"


def main() -> int:
    ASSET_TARGET.mkdir(parents=True, exist_ok=True)
    if MERMAID_SOURCE.exists():
        if MERMAID_TARGET.exists():
            shutil.rmtree(MERMAID_TARGET)
        shutil.copytree(MERMAID_SOURCE, MERMAID_TARGET)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
