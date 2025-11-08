from __future__ import annotations

import argparse
import os
import shlex
import sys
from typing import Any, Iterable, List

import pytest
from typing import Any

from doc_tools.config import paths

DEFAULT_TARGET = "packages/docs_tooling/tests"
ENV_VAR = "DOCS_PYTEST_ARGS"
COVERAGE_MODULES = ["doc_tools"]
DEFAULT_COVERAGE_THRESHOLD = 90
COVERAGE_THRESHOLD_ENV = "DOCS_COV_MIN"


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


def coverage_threshold() -> int:
    raw = os.environ.get(COVERAGE_THRESHOLD_ENV, "").strip()
    if not raw:
        return DEFAULT_COVERAGE_THRESHOLD
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_COVERAGE_THRESHOLD
    return max(0, parsed)


def main(argv: Iterable[str] | None = None) -> int:
    parsed = parse_args(argv)
    env_value = os.environ.get(ENV_VAR, "")
    pytest_args = build_pytest_args(env_value, parsed.pytest_args)
    config_path = str(paths.DOCS_PACKAGE_ROOT / "pytest.ini")
    pytest_args = ["-c", config_path, *pytest_args]
    if parsed.coverage:
        threshold = coverage_threshold()
        coverage_flags = [f"--cov={module}" for module in COVERAGE_MODULES]
        pytest_args = [
            *coverage_flags,
            "--cov-report=term-missing",
            "--cov-report=xml",
            f"--cov-fail-under={threshold}",
            *pytest_args,
        ]
    pytest_main: Any = getattr(pytest, "main")
    result = pytest_main(pytest_args)
    return int(result) if isinstance(result, int) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
