#!/usr/bin/env python3
"""Run `mkdocs build --strict` with support for dry-run builds."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MKDOCS_CONFIG = ROOT / "docs" / "config" / "mkdocs.yml"
WARNING_PATTERNS = (
    "contains a link",
    "does not contain an anchor",
    "not found among documentation files",
)


def run_mkdocs(*, dry_run: bool) -> int:
    site_dir: str | None = None
    if dry_run:
        site_dir = tempfile.mkdtemp(prefix="mkdocs-site-")
    cmd = [
        "mkdocs",
        "build",
        "--strict",
        "--config-file",
        str(MKDOCS_CONFIG),
    ]
    if site_dir is not None:
        cmd.extend(["--site-dir", site_dir])
    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        output = (result.stdout or "") + (result.stderr or "")
        if output:
            print(output, end="")
        if result.returncode != 0:
            return result.returncode
        lowered = output.lower()
        if any(pattern in lowered for pattern in WARNING_PATTERNS):
            print("mkdocs build reported documentation issues (treating as failure)", file=sys.stderr)
            return 1
        return 0
    except FileNotFoundError:
        print(
            "mkdocs binary not found; install it via `uv pip install mkdocs`.",
            file=sys.stderr,
        )
        return 1
    finally:
        if site_dir is not None:
            shutil.rmtree(site_dir, ignore_errors=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="use a temporary site directory and clean it up afterwards")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run_mkdocs(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
