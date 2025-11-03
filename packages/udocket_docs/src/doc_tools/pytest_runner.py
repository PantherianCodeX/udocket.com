from __future__ import annotations

import argparse
import os
import shlex
import sys
from pathlib import Path
from typing import Iterable, List

import pytest

DEFAULT_TARGET = "packages/udocket_docs/tests/doc_tools"
ENV_VAR = "DOCS_PYTEST_ARGS"
COVERAGE_MODULES = [
    "doc_tools.paths",
    "doc_tools.render_mermaid",
    "doc_tools.pdf_build",
    "doc_tools.hash_and_manifest",
    "doc_tools.pytest_runner",
    "doc_tools.sync.doc_assets",
    "doc_tools.sync.document_controls",
]


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute pytest for doc tooling with optional coverage and argument passthrough.",
    )
    parser.add_argument("--coverage", action="store_true", help="Enable coverage collection for doc_tools package.")
    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="Additional pytest arguments (appended after environment-provided values).",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def build_pytest_args(env_value: str | None, cli_args: Iterable[str]) -> List[str]:
    args: list[str] = []
    if env_value:
        args.extend(shlex.split(env_value))
    args.extend(cli_args)
    if not args:
        args.append(DEFAULT_TARGET)
    return args


def main(argv: Iterable[str] | None = None) -> int:
    parsed = parse_args(argv)
    env_value = os.environ.get(ENV_VAR, "")
    pytest_args = build_pytest_args(env_value, parsed.pytest_args)
    config_path = str(Path(__file__).resolve().parents[2] / 'pytest.ini')
    pytest_args = ['-c', config_path, *pytest_args]
    if parsed.coverage:
        coverage_flags = [f"--cov={module}" for module in COVERAGE_MODULES]
        pytest_args = [*coverage_flags, "--cov-report=term-missing", *pytest_args]
    return pytest.main(pytest_args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
