#!/usr/bin/env python3
"""Aggregate documentation linting for TDD.

This script wraps all of the doc hygiene checks the project expects:

* markdownlint-cli (via npx, required)
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
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from docs.tools.doc_roots import ALL_TEMPLATE_ROOTS  # noqa: E402

DEFAULT_TARGETS: tuple[Path, ...] = (ROOT / "docs" / "src",)
TDD_DOC = ROOT / "docs" / "src" / "overview" / "tdd.md"
STRUCTURE_DIRS = [ROOT / root for root in ALL_TEMPLATE_ROOTS] + [ROOT / "docs/src/ops"]


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
    markdownlint_config = str((ROOT / "docs" / "config" / ".markdownlint.json").relative_to(ROOT))
    tasks = [
        Task(
            name="runbook_catalog --check",
            cmd=[py, "-m", "docs.tools.build.runbook_catalog", "--check"],
        ),
        Task(
            name="diagram_index --check",
            cmd=[py, "-m", "docs.tools.build.diagram_index", "--check"],
        ),
        Task(
            name="api_error_codes --check",
            cmd=[py, "-m", "docs.tools.build.api_error_codes", "--check"],
        ),
        Task(
            name="sync_doc_assets.py",
            cmd=[py, "-m", "docs.tools.sync_doc_assets"],
        ),
        Task(
            name="check_structure.py",
            cmd=[
                py,
                "-m",
                "docs.tools.check_structure",
                *[str(path) for path in STRUCTURE_DIRS],
            ],
        ),
        Task(
            name="check_appendices.py",
            cmd=[py, "-m", "docs.tools.check_appendices"],
        ),
        Task(
            name="markdownlint docs/src",
            cmd=[
                "npx",
                "markdownlint-cli",
                "--config",
                markdownlint_config,
                "docs/src/**/*.md",
            ],
            install_hint="npm ci",
        ),
        Task(
            name="check_settings_keys.py",
            cmd=[py, "-m", "docs.tools.check_settings_keys"],
        ),
        Task(
            name="check_links.py",
            cmd=[py, "-m", "docs.tools.check_links"],
            env={"STRICT_DOCS": "1"},
        ),
        Task(
            name="mkdocs build --strict",
            cmd=[py, "-m", "docs.tools.build.mkdocs", "--dry-run"],
        ),
    ]
    return tasks


def resolve_targets(args: list[str]) -> list[Path]:
    if not args:
        return list(DEFAULT_TARGETS)
    resolved: list[Path] = []
    for raw in args:
        p = Path(raw)
        if not p.is_absolute():
            p = ROOT / p
        if not p.exists():
            print(f"Warning: target '{raw}' does not exist; skipping", file=sys.stderr)
            continue
        resolved.append(p)
    return resolved or list(DEFAULT_TARGETS)


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
