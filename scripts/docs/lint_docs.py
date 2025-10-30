#!/usr/bin/env python3
"""Aggregate documentation linting for TDD.

This script wraps all of the doc hygiene checks the project expects:

* markdownlint-cli2 (via npx, required)
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

DEFAULT_TARGETS = [Path("docs/src")]

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGETS = [ROOT / p for p in DEFAULT_TARGETS]
TDD_DOC = ROOT / "docs" / "src" / "overview" / "tdd.md"


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


def build_tasks(targets: list[Path]) -> list[Task]:
    py = sys.executable
    markdownlint_config = str((ROOT / "docs" / ".markdownlint.json").relative_to(ROOT))
    markdownlint_glob = "docs/src/**/*.md"
    tasks = [
        Task(
            name="build_runbook_catalog.py --check",
            cmd=[py, str(ROOT / "scripts" / "docs" / "build_runbook_catalog.py"), "--check"],
        ),
        Task(
            name="build_diagram_index.py --check",
            cmd=[py, str(ROOT / "scripts" / "docs" / "build_diagram_index.py"), "--check"],
        ),
        Task(
            name="check_structure.py",
            cmd=[
                py,
                str(ROOT / "scripts" / "docs" / "check_structure.py"),
                str(ROOT / "docs" / "src" / "services"),
                str(ROOT / "docs" / "src" / "apps"),
                str(ROOT / "docs" / "src" / "ops"),
            ],
        ),
        Task(
            name="check_appendices.py",
            cmd=[py, str(ROOT / "scripts" / "docs" / "check_appendices.py")],
        ),
        Task(
            name="markdownlint docs/src",
            cmd=[
                "npx",
                "markdownlint-cli2",
                "--config",
                markdownlint_config,
                markdownlint_glob,
            ],
            install_hint="npm ci",
        ),
        Task(
            name="markdownlint-cli2 (global)",
            cmd=["markdownlint-cli2", "--config", markdownlint_config, markdownlint_glob],
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
        Task(
            name="mkdocs build --strict",
            cmd=[py, str(ROOT / "scripts" / "docs" / "build_mkdocs.py"), "--dry-run"],
        ),
    ]
    return tasks


def resolve_targets(args: list[str]) -> list[Path]:
    if not args:
        return DEFAULT_TARGETS
    resolved: list[Path] = []
    for raw in args:
        p = Path(raw)
        if not p.is_absolute():
            p = ROOT / p
        if not p.exists():
            print(f"Warning: target '{raw}' does not exist; skipping", file=sys.stderr)
            continue
        resolved.append(p)
    return resolved or DEFAULT_TARGETS


def main() -> int:
    if not TDD_DOC.exists():
        print(f"Cannot find documentation file at {TDD_DOC}", file=sys.stderr)
        return 2

    targets = resolve_targets(sys.argv[1:])
    failures = 0
    for task in build_tasks(targets):
        if not run_task(task):
            failures += 1
    if failures:
        print(f"Documentation lint failed ({failures} task(s) errored).")
        return 1
    print("All documentation lint tasks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
