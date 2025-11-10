"""Utility helpers for invoking shell commands from the CLI."""

from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .config import REPO_ROOT

@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int


def run_command(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    check: bool = True,
) -> CommandResult:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    process = subprocess.run(  # noqa: S603
        list(argv),
        cwd=str(cwd or REPO_ROOT),
        env=merged_env,
        check=check,
    )
    return CommandResult(argv=tuple(argv), returncode=process.returncode)


def shlex_join(argv: Sequence[str]) -> str:
    return shlex.join(argv)
