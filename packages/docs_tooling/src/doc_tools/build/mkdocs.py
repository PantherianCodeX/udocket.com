#!/usr/bin/env python3
"""Run `mkdocs build --strict` with support for dry-run builds."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from subprocess import CompletedProcess
from tempfile import TemporaryDirectory
from typing import Final

from doc_tools.config import paths

REPO_ROOT: Final[Path] = paths.REPO_ROOT
MKDOCS_CONFIG: Final[Path] = paths.DOCS_PACKAGE_ROOT / "mkdocs.yml"
WARNING_PATTERNS: Final[tuple[str, ...]] = (
    "contains a link",
    "does not contain an anchor",
    "not found among documentation files",
)


def run_mkdocs(*, dry_run: bool) -> int:
    temp_dir: TemporaryDirectory[str] | None = None
    site_dir: Path | None = None
    if dry_run:
        temp_dir = TemporaryDirectory(prefix="mkdocs-site-")
        site_dir = Path(temp_dir.name)
    cmd = [
        "mkdocs",
        "build",
        "--strict",
        "--config-file",
        str(MKDOCS_CONFIG),
    ]
    if site_dir is not None:
        cmd.extend(["--site-dir", str(site_dir)])
    try:
        result: CompletedProcess[str] = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
        output_parts = [part for part in (result.stdout, result.stderr) if part]
        output = "".join(output_parts)
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
        if temp_dir is not None:
            temp_dir.cleanup()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="use a temporary site directory and clean it up afterwards")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run_mkdocs(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
