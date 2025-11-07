#!/usr/bin/env python3
"""Build MkDocs site and mirror generated assets."""

from __future__ import annotations

import sys

from doc_tools.build import mkdocs as mkdocs_build
from doc_tools.sync import doc_assets


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    # Ensure rendered diagrams are mirrored into the docs tree before build.
    mirror_status = doc_assets.main([])
    if mirror_status != 0:
        return mirror_status
    status = mkdocs_build.main(args)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
