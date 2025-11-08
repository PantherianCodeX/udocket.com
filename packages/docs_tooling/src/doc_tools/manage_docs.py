#!/usr/bin/env python3
"""Unified entry point for documentation linting, syncing, and builds."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, Sequence

from doc_tools.config import paths

REPO_ROOT = paths.REPO_ROOT
PYTHON = sys.executable

if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

DOCS_DIR = paths.DOCS_ROOT
CONFIG_DIR = paths.CONFIG_ROOT
TOOLS_DIR = Path(__file__).resolve().parent
DEFAULT_TARGETS: tuple[Path, ...] = ()
STRUCTURE_DIRS = list(paths.SERVICE_ROOTS) + [DOCS_DIR / "ops"]
VALE_CI_CONFIG = str((CONFIG_DIR / "vale-ci.ini").relative_to(REPO_ROOT))
VALE_TARGETS = [
    str((DOCS_DIR / "_template.md").relative_to(REPO_ROOT)),
    str((DOCS_DIR / "experience" / "_template.md").relative_to(REPO_ROOT)),
    str((Path("packages/docs_tooling/tests/vale_fixtures/service_valid.md"))),
]


@dataclass
class RunContext:
    dry_run: bool
    targets: list[Path]
    verbose: bool = False


CmdBuilder = Callable[[RunContext], list[str] | None]


@dataclass
class Task:
    name: str
    category: str
    builder: CmdBuilder
    optional: bool = False
    install_hint: str | None = None
    env: Dict[str, str] | None = None
    description: str | None = None
    skip_in_dry_run: bool = False


def resolve_targets(raw_targets: Sequence[str]) -> list[Path]:
    if not raw_targets:
        return list(DEFAULT_TARGETS)
    resolved: list[Path] = []
    for entry in raw_targets:
        path = Path(entry)
        if not path.is_absolute():
            path = REPO_ROOT / path
        if not path.exists():
            print(
                f"[manage-docs] warning: target '{entry}' does not exist; skipping", file=sys.stderr
            )
            continue
        resolved.append(path)
    return resolved


def python_task(*args: str) -> list[str]:
    return [PYTHON, "-m", *args]


def builder_runbook_check(_: RunContext) -> list[str]:
    return python_task("doc_tools.build.runbook_catalog", "--check")


def builder_diagram_check(_: RunContext) -> list[str]:
    return python_task("doc_tools.build.diagram_index", "--check")


def builder_api_error_codes_check(_: RunContext) -> list[str]:
    return python_task("doc_tools.build.api_error_codes", "--check")


def builder_slo_check(_: RunContext) -> list[str]:
    return python_task("doc_tools.build.slo_index", "--check")


def builder_check_structure(ctx: RunContext) -> list[str]:
    paths = ctx.targets or STRUCTURE_DIRS
    return [
        PYTHON,
        "-m",
        "doc_tools.check.structure",
        *[str(path) for path in paths],
    ]


def builder_check_doc_control_markers(ctx: RunContext) -> list[str]:
    cmd = python_task("doc_tools.check.document_controls_tags")
    if ctx.targets:
        cmd.extend(str(path) for path in ctx.targets)
    return cmd


def builder_check_appendices(_: RunContext) -> list[str]:
    return python_task("doc_tools.check.appendices")


def builder_check_templates(ctx: RunContext) -> list[str]:
    cmd = python_task("doc_tools.check.templates")
    if ctx.targets:
        cmd.extend(str(path) for path in ctx.targets)
    return cmd


def builder_markdownlint(_: RunContext) -> list[str]:
    config = str((CONFIG_DIR / ".markdownlint.json").relative_to(REPO_ROOT))
    return [
        "npx",
        "markdownlint-cli",
        "--config",
        config,
        "docs/**/*.md",
    ]


def builder_vale_sync(_: RunContext) -> list[str]:
    return [
        "vale",
        "sync",
        "--config",
        VALE_CI_CONFIG,
    ]


def builder_vale(ctx: RunContext) -> list[str]:
    cmd = [
        "vale",
        "--config",
        VALE_CI_CONFIG,
        "--minAlertLevel",
        "error",
        *VALE_TARGETS,
    ]
    return cmd


def builder_check_settings(_: RunContext) -> list[str]:
    return python_task("doc_tools.check.settings_keys")


def builder_check_links(_: RunContext) -> list[str]:
    return python_task("doc_tools.check.links")


def builder_check_asset_paths(ctx: RunContext) -> list[str]:
    targets = ctx.targets or [paths.DOCS_ROOT]
    cmd = python_task("doc_tools.check.asset_paths")
    cmd.extend(str(target) for target in targets)
    return cmd


def builder_sync_doc_controls(ctx: RunContext) -> list[str]:
    cmd = python_task("doc_tools.sync.document_controls")
    if ctx.targets:
        cmd.extend(str(p) for p in ctx.targets)
    if ctx.dry_run:
        cmd.append("--dry-run")
    return cmd


def builder_sync_doc_assets(ctx: RunContext) -> list[str]:
    cmd = python_task("doc_tools.sync.doc_assets")
    if ctx.dry_run:
        cmd.append("--dry-run")
    if ctx.verbose:
        cmd.append("--verbose")
    return cmd


def builder_sync_nav(ctx: RunContext) -> list[str]:
    cmd = python_task("doc_tools.sync.nav")
    if ctx.dry_run:
        cmd.append("--dry-run")
    return cmd


def builder_sync_nav_mapping(ctx: RunContext) -> list[str] | None:
    if ctx.dry_run:
        print("[manage-docs] dry-run: skipping nav mapping sync")
        return None
    return python_task("doc_tools.sync.nav_mapping")


def builder_runbook_update(ctx: RunContext) -> list[str]:
    if ctx.dry_run:
        return python_task("doc_tools.build.runbook_catalog", "--check")
    return python_task("doc_tools.build.runbook_catalog")


def builder_diagram_update(ctx: RunContext) -> list[str]:
    if ctx.dry_run:
        return python_task("doc_tools.build.diagram_index", "--check")
    return python_task("doc_tools.build.diagram_index")


def builder_slo_update(ctx: RunContext) -> list[str]:
    cmd = ["doc_tools.build.slo_index"]
    if ctx.dry_run:
        return python_task(*cmd, "--check")
    return python_task(*cmd)


def builder_api_error_update(ctx: RunContext) -> list[str]:
    if ctx.dry_run:
        return python_task("doc_tools.build.api_error_codes", "--check")
    return python_task("doc_tools.build.api_error_codes")


def builder_mkdocs(ctx: RunContext) -> list[str]:
    cmd = python_task("doc_tools.build.mkdocs_site")
    if ctx.dry_run:
        cmd.append("--dry-run")
    return cmd


def builder_pdf_tdd(ctx: RunContext) -> list[str] | None:
    if ctx.dry_run:
        print("[manage-docs] dry-run: skipping TDD PDF build")
        return None
    return [PYTHON, "-m", "doc_tools.build.pdf", "--target", "tdd"]


def builder_pdf_prd(ctx: RunContext) -> list[str] | None:
    if ctx.dry_run:
        print("[manage-docs] dry-run: skipping PRD PDF build")
        return None
    return [PYTHON, "-m", "doc_tools.build.pdf", "--target", "prd"]


TASKS: list[Task] = [
    Task(
        name="runbook_catalog --check",
        category="lint",
        builder=builder_runbook_check,
    ),
    Task(
        name="diagram_index --check",
        category="lint",
        builder=builder_diagram_check,
    ),
    Task(
        name="api_error_codes --check",
        category="lint",
        builder=builder_api_error_codes_check,
    ),
    Task(
        name="slo_index --check",
        category="lint",
        builder=builder_slo_check,
    ),
    Task(
        name="check_structure.py",
        category="lint",
        builder=builder_check_structure,
    ),
    Task(
        name="check_document_controls_tags.py",
        category="lint",
        builder=builder_check_doc_control_markers,
    ),
    Task(
        name="check_appendices.py",
        category="lint",
        builder=builder_check_appendices,
    ),
    Task(
        name="check_templates.py",
        category="check",
        builder=builder_check_templates,
    ),
    Task(
        name="markdownlint docs",
        category="lint",
        builder=builder_markdownlint,
        install_hint="npm ci",
    ),
    Task(
        name="vale sync",
        category="lint",
        builder=builder_vale_sync,
        install_hint="brew install vale",
    ),
    Task(
        name="vale docs",
        category="lint",
        builder=builder_vale,
        install_hint="brew install vale",
    ),
    Task(
        name="check_settings_keys.py",
        category="lint",
        builder=builder_check_settings,
    ),
    Task(
        name="check_links.py",
        category="lint",
        builder=builder_check_links,
        env={"STRICT_DOCS": "1"},
    ),
    Task(
        name="check_asset_paths.py",
        category="lint",
        builder=builder_check_asset_paths,
    ),
    Task(
        name="sync doc controls",
        category="sync",
        builder=builder_sync_doc_controls,
    ),
    Task(
        name="sync doc assets",
        category="sync",
        builder=builder_sync_doc_assets,
    ),
    Task(
        name="build diagram index",
        category="sync",
        builder=builder_diagram_update,
    ),
    Task(
        name="build runbook catalog",
        category="sync",
        builder=builder_runbook_update,
    ),
    Task(
        name="build SLO index",
        category="sync",
        builder=builder_slo_update,
    ),
    Task(
        name="build API error codes",
        category="sync",
        builder=builder_api_error_update,
    ),
    Task(
        name="sync ADR nav",
        category="sync",
        builder=builder_sync_nav,
    ),
    Task(
        name="sync nav mapping",
        category="sync-extra",
        builder=builder_sync_nav_mapping,
    ),
    Task(
        name="mkdocs build --strict",
        category="build",
        builder=builder_mkdocs,
    ),
    Task(
        name="build TDD PDF",
        category="pdf",
        builder=builder_pdf_tdd,
    ),
    Task(
        name="build PRD PDF",
        category="pdf",
        builder=builder_pdf_prd,
    ),
]


def run_task(task: Task, ctx: RunContext) -> bool:
    cmd = task.builder(ctx)
    if cmd is None:
        return True
    print(f"→ {task.name}")
    env = os.environ.copy()
    if task.env:
        env.update(task.env)
    try:
        subprocess.run(cmd, cwd=REPO_ROOT, env=env, check=True)
        print(f"✓ {task.name}\n")
        return True
    except FileNotFoundError:
        if task.optional:
            hint = f" ({task.install_hint})" if task.install_hint else ""
            print(f"⤷ Skipping optional task '{task.name}'{hint}\n")
            return True
        print(f"✗ {task.name} failed: command not found ({cmd[0]!r})\n")
        if task.install_hint:
            print(f"  Install hint: {task.install_hint}\n")
        return False
    except subprocess.CalledProcessError as exc:
        if task.optional:
            print(f"⤷ Optional task '{task.name}' failed with exit code {exc.returncode}; continuing\n")
            return True
        print(f"✗ {task.name} failed with exit code {exc.returncode}\n")
        return False


def organise_tasks(selected_categories: Iterable[str]) -> list[Task]:
    categories = set(selected_categories)
    ordered: list[Task] = []
    for task in TASKS:
        if task.category in categories:
            ordered.append(task)
    return ordered


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage documentation workflows (lint, sync, build, PDFs).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="Optional paths to scope lint/sync commands (defaults to docs/ tree).",
    )
    parser.add_argument("--lint", action="store_true", help="Run read-only lint checks.")
    parser.add_argument("--check", action="store_true", help="Run template/document checks.")
    parser.add_argument("--sync", action="store_true", help="Apply auto-generated artifacts.")
    parser.add_argument(
        "--sync-all",
        action="store_true",
        help="Run sync tasks plus optional extras (nav mapping, heavy migrations).",
    )
    parser.add_argument("--build", action="store_true", help="Build the MkDocs site.")
    parser.add_argument("--pdf", action="store_true", help="Build PDF artifacts.")
    parser.add_argument("--all", action="store_true", help="Run lint + check + sync + build + pdf.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in read-only mode (sync/build tasks verify without writing).",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose task output.")
    parser.add_argument("--list", action="store_true", help="List configured tasks and exit.")
    return parser.parse_args(argv)


def list_tasks() -> None:
    print("Available tasks:")
    for task in TASKS:
        print(f"- {task.category:>5} : {task.name}")


def determine_categories(args: argparse.Namespace) -> list[str]:
    if args.all:
        return ["lint", "check", "sync", "sync-extra", "build", "pdf"]

    ordered: list[str] = []

    def _add(category: str, enabled: bool) -> None:
        if enabled and category not in ordered:
            ordered.append(category)

    _add("lint", args.lint)
    _add("check", args.check)
    _add("sync", args.sync or args.sync_all)
    _add("sync-extra", args.sync_all)
    _add("build", args.build)
    _add("pdf", args.pdf)

    if not ordered:
        return ["lint"]
    return ordered


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.list:
        list_tasks()
        return 0

    categories = determine_categories(args)
    targets = resolve_targets(args.targets)
    ctx = RunContext(dry_run=args.dry_run, targets=targets, verbose=args.verbose)

    if any(cat in categories for cat in ("lint", "check")):
        tdd_doc = DOCS_DIR / "overview" / "tdd.md"
        if not tdd_doc.exists():
            print(f"[manage-docs] missing documentation anchor at {tdd_doc}", file=sys.stderr)
            return 2

    tasks = organise_tasks(categories)
    failures = 0
    for task in tasks:
        if not run_task(task, ctx):
            failures += 1
    if failures:
        print(f"[manage-docs] {failures} task(s) failed.\n")
        return 1
    print("[manage-docs] completed successfully.\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    raise SystemExit(main(sys.argv[1:]))
