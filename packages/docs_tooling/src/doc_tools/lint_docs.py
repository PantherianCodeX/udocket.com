#!/usr/bin/env python3
"""Backwards-compatible wrapper around `doc_tools.manage_docs --lint`."""

from __future__ import annotations

import sys
from typing import Sequence

from doc_tools.manage_docs import main as manage_main


def main(argv: Sequence[str] | None = None) -> int:
    args = ["--lint"]
    if argv is None:
        argv = sys.argv[1:]
    args.extend(argv)
    return manage_main(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
