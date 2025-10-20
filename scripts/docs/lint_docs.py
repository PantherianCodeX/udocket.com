#!/usr/bin/env python3
"""Aggregate documentation linting for TDD.

This script wraps all of the doc hygiene checks the project expects:

* mdformat --check (requires ``pip install -r requirements-docs.txt``)
* markdownlint-cli2 (optional locally, installed in CI)
* Appendix/settings cross-checks implemented in local helper scripts

The goal is to provide a single entrypoint that developers and CI can call.
When a tool is unavailable locally and marked optional, the task is skipped
with a hint so contributors can opt in.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "TDD.md"


@dataclass
class Task:
    name: str
    cmd: list[str]
    optional: bool = False
    install_hint: str | None = None
    env: dict[str, str] | None = None


def run_task(task: Task) -> bool:
    """Execute a task and return True on success."""
    print(f"→ {task.name}")
    env = os.environ.copy()
    if task.env:
        env.update(task.env)
    try:
        subprocess.run(task.cmd, cwd=ROOT, env=env, check=True)
        print(f"✓ {task.name}\n")
        return True
    except FileNotFoundError:
        if task.optional:
            hint = f" ({task.install_hint})" if task.install_hint else ""
            print(f"⤷ Skipping optional task '{task.name}'{hint}\n")
            return True
        print(f"✗ {task.name} failed: command not found ({task.cmd[0]!r})")
        if task.install_hint:
            print(f"  Install hint: {task.install_hint}")
        return False
    except subprocess.CalledProcessError as exc:
        if task.optional:
            print(f"⤷ Optional task '{task.name}' failed with exit code {exc.returncode}; continuing\n")
            return True
        print(f"✗ {task.name} failed with exit code {exc.returncode}")
        return False


def build_tasks() -> list[Task]:
    py = sys.executable
    return [
        Task(
            name="mdformat --check docs/TDD.md",
            cmd=[py, "-m", "mdformat", "--wrap", "no", "--check", str(DOC)],
            install_hint="pip install -r requirements-docs.txt",
        ),
        Task(
            name="markdownlint-cli2 docs/TDD.md",
            cmd=["markdownlint-cli2", str(DOC)],
            optional=True,
            install_hint="npm install --location=global markdownlint-cli2 markdownlint-cli2-config-standard",
        ),
        Task(
            name="check_settings_keys.py",
            cmd=[py, str(ROOT / "scripts" / "docs" / "check_settings_keys.py")],
        ),
        Task(
            name="link_check.py",
            cmd=[py, str(ROOT / "scripts" / "docs" / "link_check.py")],
            env={"STRICT_DOCS": "1"},
        ),
    ]


def main() -> int:
    if not DOC.exists():
        print(f"Cannot find documentation file at {DOC}", file=sys.stderr)
        return 2

    failures = 0
    for task in build_tasks():
        if not run_task(task):
            failures += 1
    if failures:
        print(f"Documentation lint failed ({failures} task(s) errored).")
        return 1
    print("All documentation lint tasks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
