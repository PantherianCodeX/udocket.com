"""udocket CLI entry point."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent
from typing import Callable, Sequence

from . import __version__ as CLI_VERSION
from . import config
from .helpers import (
    compose_command,
    compose_down,
    compose_exec,
    compose_logs,
    compose_ps,
    compose_restart,
    compose_shell,
    compose_up,
    docs_run_bash,
    docs_manage_docs,
    docs_module,
    docs_run_pytest,
    ensure_services,
    uv_run,
    uv_run_platform,
)
from .runner import run_command, shlex_join

TYPEWIZ_MANIFEST = Path("out/test-reports/typing/typing_audit.json")
TYPEWIZ_PATHS = (
    "apps/platform/operations",
    "packages/core/agents",
    "packages/common",
)

Handler = Callable[[argparse.Namespace], int]


def _run_images_build(images: Sequence[str], *, load: bool | None = None, push: bool | None = None) -> None:
    if config.USE_BUILD:
        flags = config.bake_image_flags(load=load, push=push)
        run_command(["docker", "buildx", "bake", *flags, *images])
    else:
        run_command(compose_command(config.BASE_COMPOSE, "build", *images))


def _capture_command(argv: Sequence[str]) -> str:
    result = subprocess.run(  # noqa: S603
        list(argv),
        cwd=config.REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if getattr(args, "version", False):
        print(f"udocket {CLI_VERSION}")
        return 0
    handler: Handler | None = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="udocket",
        description="Unified developer tooling for the uDocket platform",
    )
    parser.add_argument("--version", action="store_true", help="Print CLI version and exit")
    subparsers = parser.add_subparsers(dest="command")
    _register_ci(subparsers)
    _register_tests(subparsers)
    _register_typing(subparsers)
    _register_docs(subparsers)
    _register_stack(subparsers)
    _register_uv(subparsers)
    _register_doctools(subparsers)
    _register_devcontainer(subparsers)
    _register_docsite(subparsers)
    _register_clean(subparsers)
    _register_typewiz(subparsers)
    _register_shells(subparsers)
    _register_db(subparsers)
    _register_keycloak(subparsers)
    _register_redis(subparsers)
    _register_images(subparsers)
    _register_docker(subparsers)
    return parser


def _register_ci(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    ci = subparsers.add_parser("ci", help="Continuous integration helpers")
    ci_sub = ci.add_subparsers(dest="ci_command", required=True)

    precommit = ci_sub.add_parser("precommit-install", help="Install and configure git hooks")
    precommit.set_defaults(handler=_handle_ci_precommit)

    check = ci_sub.add_parser("check", help="Run typing, docs lint, and test suites")
    check.set_defaults(handler=_handle_ci_check)


def _handle_ci_precommit(_: argparse.Namespace) -> int:
    run_command([config.UV_BIN, "pip", "install", "--quiet", "pre-commit"], check=False)
    run_command(["pre-commit", "install"])
    return 0


def _handle_ci_check(_: argparse.Namespace) -> int:
    _handle_typing_run(argparse.Namespace())
    _handle_docs_lint(argparse.Namespace())
    _handle_tests_all(argparse.Namespace())
    return 0


def _register_tests(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    tests = subparsers.add_parser("tests", help="Execute pytest suites and helpers")
    tests_sub = tests.add_subparsers(dest="tests_command", required=True)

    all_parser = tests_sub.add_parser("all", help="Run all automated test suites")
    all_parser.set_defaults(handler=_handle_tests_all)

    pytest_parser = tests_sub.add_parser("pytest", help="Run pytest with optional arguments")
    pytest_parser.add_argument("pytest_args", nargs=argparse.REMAINDER, help="Arguments forwarded to pytest")
    pytest_parser.set_defaults(handler=_handle_pytest_default)

    verbose = tests_sub.add_parser("pytest-verbose", help="Run pytest -v")
    verbose.set_defaults(handler=_handle_pytest_verbose)

    failfast = tests_sub.add_parser("pytest-failfast", help="Run pytest -x")
    failfast.set_defaults(handler=_handle_pytest_failfast)

    cov = tests_sub.add_parser("pytest-cov", help="Run pytest with coverage")
    cov.set_defaults(handler=_handle_pytest_cov)

    clean = tests_sub.add_parser("pytest-clean", help="Remove pytest cache directories")
    clean.set_defaults(handler=_handle_pytest_clean)

    common = tests_sub.add_parser("common", help="Run packages.common test suite")
    common.set_defaults(handler=_handle_tests_common)

    core = tests_sub.add_parser("core", help="Run packages.core test suite")
    core.set_defaults(handler=_handle_tests_core)

    platform = tests_sub.add_parser("platform", help="Run platform test suite")
    platform.set_defaults(handler=_handle_tests_platform)


def _handle_tests_all(_: argparse.Namespace) -> int:
    _handle_tests_common(argparse.Namespace())
    _handle_tests_core(argparse.Namespace())
    _handle_tests_platform(argparse.Namespace())
    _handle_docs_test(argparse.Namespace())
    return 0


def _handle_pytest_default(args: argparse.Namespace) -> int:
    uv_run("apps/platform", "pytest", *args.pytest_args, extras=("dev",))
    return 0


def _handle_pytest_verbose(_: argparse.Namespace) -> int:
    uv_run("apps/platform", "pytest", "-v", extras=("dev",))
    return 0


def _handle_pytest_failfast(_: argparse.Namespace) -> int:
    uv_run("apps/platform", "pytest", "-x", extras=("dev",))
    return 0


def _handle_pytest_cov(_: argparse.Namespace) -> int:
    uv_run("apps/platform", "pytest", "--cov=apps/platform", extras=("dev",))
    return 0


def _handle_pytest_clean(_: argparse.Namespace) -> int:
    run_command(["rm", "-rf", ".pytest_cache"])
    return 0


def _handle_tests_common(_: argparse.Namespace) -> int:
    uv_run("apps/platform", "pytest", "-n", "auto", "-q", "packages/common", extras=("dev",))
    return 0


def _handle_tests_core(_: argparse.Namespace) -> int:
    uv_run("apps/platform", "pytest", "-n", "auto", "-q", "tests/packages/core", extras=("dev",))
    return 0


def _handle_tests_platform(_: argparse.Namespace) -> int:
    uv_run("apps/platform", "pytest", "-n", "auto", "-q", extras=("dev",))
    return 0


def _register_typing(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    typing_parser = subparsers.add_parser("typing", help="Typing and lint orchestration")
    typing_sub = typing_parser.add_subparsers(dest="typing_command", required=True)

    run_cmd = typing_sub.add_parser("run", help="Run baseline and strict typing checks")
    run_cmd.set_defaults(handler=_handle_typing_run)

    baseline = typing_sub.add_parser("baseline", help="Run pyright/mypy baseline checks")
    baseline.set_defaults(handler=_handle_typing_baseline)

    strict = typing_sub.add_parser("strict", help="Enforce strict typing gates")
    strict.set_defaults(handler=_handle_typing_strict)

    ci = typing_sub.add_parser("ci", help="CI-focused Typewiz dashboards")
    ci.set_defaults(handler=_handle_typing_ci)

    ai = typing_sub.add_parser("ai", help="Type checking for packages/ai")
    ai_sub = ai.add_subparsers(dest="typing_ai_command", required=True)

    ai_mypy = ai_sub.add_parser("mypy", help="Run mypy for packages/ai")
    ai_mypy.set_defaults(handler=_handle_typing_ai_mypy)

    ai_pyright = ai_sub.add_parser("pyright", help="Run pyright for packages/ai")
    ai_pyright.set_defaults(handler=_handle_typing_ai_pyright)

    ai_ruff = ai_sub.add_parser("ruff", help="Run Ruff for packages/ai")
    ai_ruff.set_defaults(handler=_handle_typing_ai_ruff)


def _ensure_typewiz_dir() -> None:
    TYPEWIZ_MANIFEST.parent.mkdir(parents=True, exist_ok=True)


def _handle_typing_run(_: argparse.Namespace) -> int:
    _handle_typing_baseline(argparse.Namespace())
    _handle_typing_strict(argparse.Namespace())
    return 0


def _handle_typing_baseline(_: argparse.Namespace) -> int:
    _ensure_typewiz_dir()
    uv_run(
        "apps/platform",
        "typewiz",
        "audit",
        "--mode",
        "current",
        "--fail-on",
        "warnings",
        "--manifest",
        str(TYPEWIZ_MANIFEST),
        "--readiness",
        "--readiness-status",
        "blocked",
        "--readiness-status",
        "ready",
        *TYPEWIZ_PATHS,
        extras=("dev",),
    )
    uv_run_platform("mypy")
    _handle_typing_ai_mypy(argparse.Namespace())
    _handle_typing_ai_pyright(argparse.Namespace())
    _handle_typing_ai_ruff(argparse.Namespace())
    return 0


def _handle_typing_strict(_: argparse.Namespace) -> int:
    run_command([config.PYTHON_BIN, "scripts/typing/ci_enforce_strict.py"])
    run_command([config.PYTHON_BIN, "scripts/typing/check_strict.py", "--tool", "both"])
    readiness_args = [
        "typewiz",
        "readiness",
        "--manifest",
        str(TYPEWIZ_MANIFEST),
        "--level",
        config.TYPEWIZ_LEVEL,
        "--limit",
        config.TYPEWIZ_LIMIT,
    ]
    for status in config.TYPEWIZ_STATUSES:
        readiness_args.extend(["--status", status])
    # Allow readiness command to succeed even if it reports blockers
    try:
        uv_run("apps/platform", *readiness_args, extras=("dev",))
    except Exception:  # pragma: no cover - readiness allowed to fail
        pass
    return 0


def _handle_typing_ci(_: argparse.Namespace) -> int:
    args_common = list(TYPEWIZ_PATHS)
    uv_run(
        "apps/platform",
        "typewiz",
        "audit",
        "--max-depth",
        "3",
        "--mode",
        "full",
        "--manifest",
        str(TYPEWIZ_MANIFEST),
        "--readiness",
        "--readiness-status",
        "blocked",
        "--readiness-status",
        "ready",
        *args_common,
        no_sync=True,
    )
    uv_run(
        "apps/platform",
        "typewiz",
        "dashboard",
        "--manifest",
        str(TYPEWIZ_MANIFEST),
        "--format",
        "json",
        "--output",
        "out/test-reports/typing/dashboard.json",
        no_sync=True,
    )
    uv_run(
        "apps/platform",
        "typewiz",
        "dashboard",
        "--manifest",
        str(TYPEWIZ_MANIFEST),
        "--format",
        "markdown",
        "--output",
        "out/test-reports/typing/dashboard.md",
        no_sync=True,
    )
    uv_run(
        "apps/platform",
        "typewiz",
        "dashboard",
        "--manifest",
        str(TYPEWIZ_MANIFEST),
        "--format",
        "html",
        "--output",
        "out/test-reports/typing/dashboard.html",
        no_sync=True,
    )
    return 0


def _handle_typing_ai_mypy(_: argparse.Namespace) -> int:
    uv_run(
        "apps/platform",
        "mypy",
        "--config-file",
        "packages/ai/mypy.ini",
        "packages/ai",
        extras=("dev",),
    )
    return 0


def _handle_typing_ai_pyright(_: argparse.Namespace) -> int:
    uv_run(
        "apps/platform",
        "pyright",
        "--project",
        "packages/ai/pyrightconfig.json",
        extras=("dev",),
    )
    return 0


def _handle_typing_ai_ruff(_: argparse.Namespace) -> int:
    uv_run(
        "packages/common",
        "python",
        "-m",
        "ruff",
        "check",
        "packages/ai",
        "--config",
        "packages/ai/ruff.toml",
        extras=("dev",),
    )
    return 0


def _handle_docs_build(_: argparse.Namespace) -> int:
    docs_manage_docs("--build")
    return 0


def _handle_docs_lint(_: argparse.Namespace) -> int:
    docs_manage_docs("--lint")
    return 0


def _handle_docs_sync(_: argparse.Namespace) -> int:
    docs_manage_docs("--sync", "--verbose")
    return 0


def _handle_docs_sync_all(_: argparse.Namespace) -> int:
    docs_manage_docs("--sync-all", "--verbose")
    return 0


def _handle_docs_sync_nav(_: argparse.Namespace) -> int:
    docs_module("doc_tools.sync.nav")
    return 0


def _handle_docs_sync_nav_mapping(_: argparse.Namespace) -> int:
    docs_module("doc_tools.sync.nav_mapping")
    return 0


def _handle_docs_sync_runbooks(_: argparse.Namespace) -> int:
    docs_module("doc_tools.build.runbook_catalog")
    return 0


def _handle_docs_check_runbooks(_: argparse.Namespace) -> int:
    docs_module("doc_tools.build.runbook_catalog", "--check")
    return 0


def _handle_docs_sync_api_codes(_: argparse.Namespace) -> int:
    docs_module("doc_tools.build.api_error_codes")
    return 0


def _handle_docs_check_api_codes(_: argparse.Namespace) -> int:
    docs_module("doc_tools.build.api_error_codes", "--check")
    return 0


def _handle_docs_sync_slo(_: argparse.Namespace) -> int:
    docs_module("doc_tools.build.slo_index")
    return 0


def _handle_docs_check_slo(_: argparse.Namespace) -> int:
    docs_module("doc_tools.build.slo_index", "--check")
    return 0


def _handle_docs_sync_diagrams(_: argparse.Namespace) -> int:
    docs_module("doc_tools.build.diagram_index")
    return 0


def _handle_docs_check_diagrams(_: argparse.Namespace) -> int:
    docs_module("doc_tools.build.diagram_index", "--check")
    return 0


def _handle_docs_sync_trees(_: argparse.Namespace) -> int:
    print(
        "docs.sync.trees is locked until the repository structure matches the appendix.",
        file=sys.stderr,
    )
    print("Skip this command until the tree refactor completes.", file=sys.stderr)
    return 1


def _handle_docs_check_nav(_: argparse.Namespace) -> int:
    docs_module("doc_tools.sync.nav", "--dry-run")
    return 0


def _handle_docs_check_trees(_: argparse.Namespace) -> int:
    docs_module("doc_tools.check.repository_trees")
    return 0


def _handle_docs_check_build(_: argparse.Namespace) -> int:
    import shutil
    import tempfile

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        docs_module("doc_tools.sync.doc_assets", "--dry-run")
        docs_module("doc_tools.check.asset_paths", "docs")
        docs_module("doc_tools.build.diagram_index", "--check")
        docs_run_bash(
            shlex_join(
                [
                    config.UV_BIN,
                    "run",
                    "--project",
                    "packages/docs_tooling",
                    "--extra",
                    "dev",
                    "mkdocs",
                    "build",
                    "--strict",
                    "--site-dir",
                    str(tmp_dir),
                    "--config-file",
                    "packages/docs_tooling/mkdocs.yml",
                ]
            )
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return 0


def _handle_docs_check_all(_: argparse.Namespace) -> int:
    _handle_docs_check_nav(argparse.Namespace())
    _handle_docs_check_runbooks(argparse.Namespace())
    _handle_docs_check_api_codes(argparse.Namespace())
    _handle_docs_check_slo(argparse.Namespace())
    _handle_docs_check_diagrams(argparse.Namespace())
    _handle_docs_check_build(argparse.Namespace())
    return 0


def _handle_docs_clean(_: argparse.Namespace) -> int:
    run_command(["rm", "-rf", "docs/build"])
    run_command(["rm", "-rf", "packages/docs_tooling/build"])
    return 0


def _handle_docs_test(args: argparse.Namespace) -> int:
    docs_run_pytest(args.pytest_args or [])
    return 0


def _handle_docs_test_coverage(args: argparse.Namespace) -> int:
    docs_run_pytest(args.pytest_args or [], coverage=True)
    return 0


def _register_docs(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    docs = subparsers.add_parser("docs", help="Docs toolbox commands")
    docs_sub = docs.add_subparsers(dest="docs_command", required=True)

    for name, handler, help_text in (
        ("build", _handle_docs_build, "Render docs output"),
        ("lint", _handle_docs_lint, "Run docs linting"),
        ("sync", _handle_docs_sync, "Sync docs artifacts"),
        ("sync-all", _handle_docs_sync_all, "Sync docs plus optional extras"),
        ("sync-nav", _handle_docs_sync_nav, "Update navigation entries"),
        ("sync-nav-mapping", _handle_docs_sync_nav_mapping, "Apply nav mapping migration"),
        ("sync-runbooks", _handle_docs_sync_runbooks, "Refresh runbook catalog"),
        ("sync-api-codes", _handle_docs_sync_api_codes, "Refresh API error codes"),
        ("sync-slo", _handle_docs_sync_slo, "Refresh SLO appendix"),
        ("sync-diagrams", _handle_docs_sync_diagrams, "Refresh diagrams index"),
        ("sync-trees", _handle_docs_sync_trees, "Refresh repository tree appendix"),
        ("check-nav", _handle_docs_check_nav, "Check nav entries"),
        ("check-runbooks", _handle_docs_check_runbooks, "Check runbook appendix"),
        ("check-api-codes", _handle_docs_check_api_codes, "Check API codes appendix"),
        ("check-slo", _handle_docs_check_slo, "Check SLO appendix"),
        ("check-diagrams", _handle_docs_check_diagrams, "Check diagram appendix"),
        ("check-trees", _handle_docs_check_trees, "Check repository tree appendix"),
        ("check-build", _handle_docs_check_build, "Validate docs build prerequisites"),
        ("check", _handle_docs_check_all, "Run all docs checks"),
        ("clean", _handle_docs_clean, "Remove built docs artifacts"),
    ):
        parser = docs_sub.add_parser(name, help=help_text)
        parser.set_defaults(handler=handler)

    test = docs_sub.add_parser("test", help="Docs pytest helpers")
    test_sub = test.add_subparsers(dest="docs_test_command", required=True)

    test_run = test_sub.add_parser("run", help="Run docs pytest suite")
    test_run.add_argument("pytest_args", nargs=argparse.REMAINDER, help="Arguments forwarded to pytest")
    test_run.set_defaults(handler=_handle_docs_test)

    test_cov = test_sub.add_parser("coverage", help="Run docs pytest with coverage")
    test_cov.add_argument("pytest_args", nargs=argparse.REMAINDER, help="Arguments forwarded to pytest")
    test_cov.set_defaults(handler=_handle_docs_test_coverage)


def _register_stack(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    stack = subparsers.add_parser("stack", help="Manage development stack services")
    stack_sub = stack.add_subparsers(dest="stack_command", required=True)

    up = stack_sub.add_parser("up", help="Start stack services detached")
    up.add_argument("--services", nargs="*", help="Subset of services to start")
    up.set_defaults(handler=_handle_stack_up)

    down = stack_sub.add_parser("down", help="Stop stack services")
    down.set_defaults(handler=_handle_stack_down)

    build = stack_sub.add_parser("build", help="Build platform and keycloak images")
    build.set_defaults(handler=_handle_stack_build)

    restart = stack_sub.add_parser("restart", help="Restart services")
    restart.add_argument("--services", nargs="*", help="Services to restart")
    restart.set_defaults(handler=_handle_stack_restart)

    logs = stack_sub.add_parser("logs", help="Tail stack logs")
    logs.add_argument("--services", nargs="*", help="Services to follow")
    logs.add_argument("--no-follow", action="store_true", help="Disable following logs")
    logs.set_defaults(handler=_handle_stack_logs)

    ps = stack_sub.add_parser("ps", help="Show stack container status")
    ps.set_defaults(handler=_handle_stack_ps)

    smoke = stack_sub.add_parser("smoke", help="Quick check that stack resolves and runs")
    smoke.set_defaults(handler=_handle_stack_smoke)

    exec_parser = stack_sub.add_parser("exec", help="Run a command inside a service container")
    exec_parser.add_argument("service", default=config.DEFAULT_SERVICE, help="Target service name")
    exec_parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to execute")
    exec_parser.set_defaults(handler=_handle_stack_exec)

    prod = subparsers.add_parser("stack-prod", help="Manage production overlay stack")
    prod_sub = prod.add_subparsers(dest="stack_prod_command", required=True)
    for name, handler, help_text in (
        ("up", _handle_stack_prod_up, "Start production stack"),
        ("down", _handle_stack_prod_down, "Stop production stack"),
        ("logs", _handle_stack_prod_logs, "Tail production stack logs"),
        ("ps", _handle_stack_prod_ps, "Show production stack status"),
    ):
        parser = prod_sub.add_parser(name, help=help_text)
        if name == "logs":
            parser.add_argument("--no-follow", action="store_true", help="Disable log following")
        parser.set_defaults(handler=handler)


def _register_uv(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    uv_group = subparsers.add_parser("uv", help="uv virtual environment helpers")
    uv_sub = uv_group.add_subparsers(dest="uv_command", required=True)

    sync_all = uv_sub.add_parser("sync", help="Sync platform and docs environments")
    sync_all.set_defaults(handler=_handle_uv_sync_all)

    platform = uv_sub.add_parser("platform", help="Platform venv helpers")
    platform_sub = platform.add_subparsers(dest="uv_platform_cmd", required=True)

    platform_sync = platform_sub.add_parser("sync", help="Sync the platform venv")
    platform_sync.set_defaults(handler=_handle_uv_platform_sync)

    platform_clean = platform_sub.add_parser("clean", help="Remove the platform venv")
    platform_clean.set_defaults(handler=_handle_uv_platform_clean)

    platform_reset = platform_sub.add_parser("reset", help="Clean + sync the platform venv")
    platform_reset.set_defaults(handler=_handle_uv_platform_reset)

    docs = uv_sub.add_parser("doctools", help="Docs tooling venv helpers")
    docs_sub = docs.add_subparsers(dest="uv_docs_cmd", required=True)

    docs_sync = docs_sub.add_parser("sync", help="Sync the docs tooling venv")
    docs_sync.set_defaults(handler=_handle_uv_docs_sync)

    docs_clean = docs_sub.add_parser("clean", help="Remove the docs tooling venv")
    docs_clean.set_defaults(handler=_handle_uv_docs_clean)

    docs_reset = docs_sub.add_parser("reset", help="Clean + sync the docs venv")
    docs_reset.set_defaults(handler=_handle_uv_docs_reset)

    cache_clean = uv_sub.add_parser("cache-clean", help="Remove uv caches")
    cache_clean.set_defaults(handler=_handle_uv_cache_clean)


def _register_doctools(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    tools = subparsers.add_parser("doctools", help="Docs toolbox environment commands")
    tools_sub = tools.add_subparsers(dest="doctools_command", required=True)

    build = tools_sub.add_parser("build", help="Build the docs toolbox image")
    build.set_defaults(handler=_handle_doctools_build)

    up = tools_sub.add_parser("up", help="Start the docs toolbox service")
    up.set_defaults(handler=_handle_doctools_up)

    down = tools_sub.add_parser("down", help="Stop the docs toolbox service")
    down.set_defaults(handler=_handle_doctools_down)

    shell = tools_sub.add_parser("shell", help="Open a shell in the docs toolbox container")
    shell.set_defaults(handler=_handle_doctools_shell)


def _register_devcontainer(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    dev = subparsers.add_parser("devcontainer", help="Manage the devcontainer service")
    dev_sub = dev.add_subparsers(dest="devcontainer_command", required=True)

    build = dev_sub.add_parser("build", help="Build the devcontainer image")
    build.set_defaults(handler=_handle_devcontainer_build)

    up = dev_sub.add_parser("up", help="Start the devcontainer service")
    up.set_defaults(handler=_handle_devcontainer_up)

    down = dev_sub.add_parser("down", help="Stop the devcontainer stack")
    down.set_defaults(handler=_handle_devcontainer_down)

    shell = dev_sub.add_parser("shell", help="Open a shell inside the devcontainer")
    shell.set_defaults(handler=_handle_devcontainer_shell)


def _register_docsite(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    docsite = subparsers.add_parser("docsite", help="MkDocs live-reload server helpers")
    docsite_sub = docsite.add_subparsers(dest="docsite_command", required=True)

    up = docsite_sub.add_parser("up", help="Start the MkDocs dev server")
    up.add_argument("--addr", default=config.DOCSITE_ADDR, help="Bind address")
    up.add_argument("--port", type=int, default=config.DOCSITE_PORT, help="Host port")
    up.add_argument("--host", default=config.DOCSITE_HOST, help="Public host name")
    up.set_defaults(handler=_handle_docsite_up)

    down = docsite_sub.add_parser("down", help="Stop the MkDocs dev server")
    down.set_defaults(handler=_handle_docsite_down)

    restart = docsite_sub.add_parser("restart", help="Restart the MkDocs dev server")
    restart.add_argument("--addr", default=config.DOCSITE_ADDR)
    restart.add_argument("--port", type=int, default=config.DOCSITE_PORT)
    restart.add_argument("--host", default=config.DOCSITE_HOST)
    restart.set_defaults(handler=_handle_docsite_restart)

    clean = docsite_sub.add_parser("clean", help="Stop server and clean artifacts")
    clean.set_defaults(handler=_handle_docsite_clean)

    build = docsite_sub.add_parser("build", help="Build docs output (alias for docs build)")
    build.set_defaults(handler=_handle_docs_build)

    launch = docsite_sub.add_parser("launch", help="Open the running docsite in a browser")
    launch.add_argument("--host", default=config.DOCSITE_HOST, help="Host name")
    launch.add_argument("--port", type=int, default=config.DOCSITE_PORT, help="Port")
    launch.set_defaults(handler=_handle_docsite_launch)

    preview = docsite_sub.add_parser("preview", help="Preview the last built docs output")
    preview.set_defaults(handler=_handle_docsite_preview)


def _register_clean(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    clean = subparsers.add_parser("clean", help="Remove cache artifacts")
    clean_sub = clean.add_subparsers(dest="clean_command", required=True)

    mypy = clean_sub.add_parser("mypy", help="Remove mypy cache")
    mypy.set_defaults(handler=_handle_clean_mypy)

    pyright = clean_sub.add_parser("pyright", help="Remove pyright cache")
    pyright.set_defaults(handler=_handle_clean_pyright)

    pycache = clean_sub.add_parser("pycache", help="Remove Python bytecode caches")
    pycache.set_defaults(handler=_handle_clean_pycache)

    coverage = clean_sub.add_parser("coverage", help="Remove coverage artifacts")
    coverage.set_defaults(handler=_handle_clean_coverage)

    clean_all = clean_sub.add_parser("all", help="Run all cleanup commands")
    clean_all.set_defaults(handler=_handle_clean_all)


def _register_typewiz(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    typewiz_group = subparsers.add_parser("typewiz", help="Typewiz helpers")
    typewiz_sub = typewiz_group.add_subparsers(dest="typewiz_command", required=True)

    audit = typewiz_sub.add_parser("audit", help="Generate Typewiz audit manifest")
    audit.set_defaults(handler=_handle_typewiz_audit)

    dashboard = typewiz_sub.add_parser("dashboard", help="Render Typewiz dashboards")
    dashboard.set_defaults(handler=_handle_typewiz_dashboard)

    readiness = typewiz_sub.add_parser("readiness", help="Show Typewiz readiness summary")
    readiness.set_defaults(handler=_handle_typewiz_readiness)

    clean = typewiz_sub.add_parser("clean", help="Remove Typewiz caches")
    clean.set_defaults(handler=_handle_typewiz_clean)


def _register_shells(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    shells = subparsers.add_parser("shell", help="Convenience shells inside containers")
    shells_sub = shells.add_subparsers(dest="shell_command", required=True)

    platform = shells_sub.add_parser("platform", help="Enter the platform container shell")
    platform.set_defaults(handler=_handle_shell_platform)

    worker = shells_sub.add_parser("worker", help="Enter the worker container shell")
    worker.set_defaults(handler=_handle_shell_worker)

    beat = shells_sub.add_parser("beat", help="Enter the beat container shell")
    beat.set_defaults(handler=_handle_shell_beat)


def _register_db(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    db = subparsers.add_parser("db", help="Database helpers")
    db_sub = db.add_subparsers(dest="db_command", required=True)

    psql = db_sub.add_parser("psql", help="Connect to primary PostgreSQL using psql")
    psql.set_defaults(handler=_handle_db_psql)


def _register_keycloak(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    keycloak = subparsers.add_parser("keycloak", help="Keycloak service helpers")
    keycloak_sub = keycloak.add_subparsers(dest="keycloak_command", required=True)

    shell = keycloak_sub.add_parser("shell", help="Open a shell in the Keycloak container")
    shell.set_defaults(handler=_handle_keycloak_shell)

    psql = keycloak_sub.add_parser("psql", help="Connect to Keycloak database")
    psql.set_defaults(handler=_handle_keycloak_psql)


def _register_redis(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    redis = subparsers.add_parser("redis", help="Redis helpers")
    redis_sub = redis.add_subparsers(dest="redis_command", required=True)

    shell = redis_sub.add_parser("shell", help="Open redis-cli inside the container")
    shell.set_defaults(handler=_handle_redis_shell)

    ping = redis_sub.add_parser("ping", help="Run a Redis PING health check")
    ping.set_defaults(handler=_handle_redis_ping)


def _register_images(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    images = subparsers.add_parser("images", help="Image build helpers")
    images_sub = images.add_subparsers(dest="images_command", required=True)

    build = images_sub.add_parser("build", help="Build container images via Buildx")
    build.add_argument("--images", nargs="*", default=list(config.IMAGES), help="Images to build")
    build.set_defaults(handler=_handle_images_build)

    load = images_sub.add_parser("load", help="Build images and load into local Docker")
    load.add_argument("--images", nargs="*", default=list(config.IMAGES))
    load.set_defaults(handler=_handle_images_load)

    push = images_sub.add_parser("push", help="Build images and push to configured registry")
    push.add_argument("--images", nargs="*", default=list(config.IMAGES))
    push.set_defaults(handler=_handle_images_push)

    cache = images_sub.add_parser("cache-warm", help="Prime toolchain layers via cache target")
    cache.set_defaults(handler=_handle_images_cache_warm)

    prod = images_sub.add_parser("build-prod", help="Build images using production compose overlays")
    prod.add_argument("--images", nargs="*", default=list(config.IMAGES))
    prod.set_defaults(handler=_handle_images_build_prod)


def _register_docker(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    docker = subparsers.add_parser("docker", help="Docker maintenance helpers")
    docker_sub = docker.add_subparsers(dest="docker_command", required=True)

    system_parent = docker_sub.add_parser("system", help="Docker system helpers")
    system_sub = system_parent.add_subparsers(dest="docker_system_cmd", required=True)
    system_sub.add_parser("du", help="Show docker disk usage").set_defaults(handler=_handle_docker_du)
    system_sub.add_parser("prune", help="Prune docker system").set_defaults(handler=_handle_docker_prune)
    system_sub.add_parser("reset", help="Run full docker cleanup").set_defaults(handler=_handle_docker_reset)

    contexts = docker_sub.add_parser("contexts", help="Docker context helpers")
    contexts_sub = contexts.add_subparsers(dest="docker_context_cmd", required=True)
    contexts_sub.add_parser("list", help="List docker contexts").set_defaults(handler=_handle_docker_context_list)
    remove = contexts_sub.add_parser("remove", help="Remove a context")
    remove.add_argument("name", help="Context name")
    remove.set_defaults(handler=_handle_docker_context_remove)
    contexts_sub.add_parser("clean", help="Remove non-default contexts").set_defaults(handler=_handle_docker_context_clean)

    containers = docker_sub.add_parser("containers", help="Container helpers")
    containers_sub = containers.add_subparsers(dest="docker_containers_cmd", required=True)
    containers_sub.add_parser("list", help="List all containers").set_defaults(handler=_handle_docker_containers_list)
    containers_sub.add_parser("list-running", help="List running containers").set_defaults(handler=_handle_docker_containers_list_running)
    containers_sub.add_parser("stop-all", help="Stop all containers").set_defaults(handler=_handle_docker_containers_stop_all)
    containers_sub.add_parser("remove-all", help="Remove all containers").set_defaults(handler=_handle_docker_containers_remove_all)
    containers_sub.add_parser("prune", help="Prune stopped containers").set_defaults(handler=_handle_docker_containers_prune)
    containers_sub.add_parser("reset", help="Stop and remove all containers").set_defaults(handler=_handle_docker_containers_reset)

    images = docker_sub.add_parser("images", help="Docker image helpers")
    images_subcmd = images.add_subparsers(dest="docker_images_cmd", required=True)
    images_subcmd.add_parser("list", help="List images").set_defaults(handler=_handle_docker_images_list)
    images_subcmd.add_parser("remove-all", help="Remove all images").set_defaults(handler=_handle_docker_images_remove_all)
    images_subcmd.add_parser("prune", help="Prune dangling images").set_defaults(handler=_handle_docker_images_prune)
    images_subcmd.add_parser("reset", help="Remove all images").set_defaults(handler=_handle_docker_images_reset)

    networks = docker_sub.add_parser("networks", help="Docker network helpers")
    networks_sub = networks.add_subparsers(dest="docker_networks_cmd", required=True)
    networks_sub.add_parser("list", help="List networks").set_defaults(handler=_handle_docker_networks_list)
    networks_sub.add_parser("prune", help="Prune networks").set_defaults(handler=_handle_docker_networks_prune)
    networks_sub.add_parser("reset", help="Remove all networks").set_defaults(handler=_handle_docker_networks_reset)

    volumes = docker_sub.add_parser("volumes", help="Docker volume helpers")
    volumes_sub = volumes.add_subparsers(dest="docker_volumes_cmd", required=True)
    volumes_sub.add_parser("list", help="List volumes").set_defaults(handler=_handle_docker_volumes_list)
    volumes_sub.add_parser("prune", help="Prune volumes").set_defaults(handler=_handle_docker_volumes_prune)
    volumes_sub.add_parser("reset", help="Remove all volumes").set_defaults(handler=_handle_docker_volumes_reset)

    compose = docker_sub.add_parser("compose", help="Compose reset helpers")
    compose_sub = compose.add_subparsers(dest="docker_compose_cmd", required=True)
    compose_sub.add_parser("ps", help="Show project compose status").set_defaults(handler=_handle_docker_compose_ps)
    compose_sub.add_parser("reset", help="Down + remove images/volumes/orphans").set_defaults(handler=_handle_docker_compose_reset)
    compose_sub.add_parser("reset-all", help="Full compose cleanup").set_defaults(handler=_handle_docker_compose_reset_all)

    buildx = docker_sub.add_parser("buildx", help="Buildx helpers")
    buildx_sub = buildx.add_subparsers(dest="docker_buildx_cmd", required=True)
    buildx_sub.add_parser("du", help="Show BuildKit cache usage").set_defaults(handler=_handle_buildx_du)
    buildx_sub.add_parser("setup", help="Ensure builder is created").set_defaults(handler=_handle_buildx_setup)
    buildx_sub.add_parser("inspect", help="Inspect builder").set_defaults(handler=_handle_buildx_inspect)
    buildx_sub.add_parser("clean", help="Remove Buildx cache directory").set_defaults(handler=_handle_buildx_clean)
    buildx_sub.add_parser("prune", help="Prune BuildKit cache").set_defaults(handler=_handle_buildx_prune)
    buildx_sub.add_parser("reset", help="Refresh Buildx caches").set_defaults(handler=_handle_buildx_reset)
    buildx_sub.add_parser("reset-builders", help="Remove non-default builders").set_defaults(handler=_handle_buildx_reset_builders)
    buildx_sub.add_parser("reset-all", help="Full Buildx cleanup").set_defaults(handler=_handle_buildx_reset_all)


def _stack_services(services: Sequence[str] | None) -> list[str]:
    return ensure_services(services, config.STACK_SERVICES)


def _handle_stack_up(args: argparse.Namespace) -> int:
    compose_up(config.DEV_COMPOSE, _stack_services(args.services))
    return 0


def _handle_stack_down(_: argparse.Namespace) -> int:
    compose_down(config.DEV_COMPOSE)
    return 0


def _handle_stack_build(_: argparse.Namespace) -> int:
    _run_images_build(("platform", "keycloak"), load=True)
    return 0


def _handle_stack_restart(args: argparse.Namespace) -> int:
    compose_restart(config.DEV_COMPOSE, _stack_services(args.services))
    return 0


def _handle_stack_logs(args: argparse.Namespace) -> int:
    compose_logs(
        config.DEV_COMPOSE,
        _stack_services(args.services),
        follow=not args.no_follow,
    )
    return 0


def _handle_stack_ps(_: argparse.Namespace) -> int:
    compose_ps(config.DEV_COMPOSE)
    return 0


def _handle_stack_smoke(_: argparse.Namespace) -> int:
    run_command(compose_command(config.DEV_COMPOSE, "config", "--services"))
    compose_ps(config.DEV_COMPOSE)
    return 0


def _handle_stack_exec(args: argparse.Namespace) -> int:
    cmd = args.cmd or []
    if not cmd:
        raise SystemExit("Provide a command to execute")
    compose_exec(config.DEV_COMPOSE, args.service, "bash", "-lc", shlex_join(cmd))
    return 0


def _handle_stack_prod_up(_: argparse.Namespace) -> int:
    compose_up(config.PROD_COMPOSE, detach=True, services=None)
    return 0


def _handle_stack_prod_down(_: argparse.Namespace) -> int:
    compose_down(config.PROD_COMPOSE)
    return 0


def _handle_stack_prod_logs(args: argparse.Namespace) -> int:
    compose_logs(config.PROD_COMPOSE, None, follow=not args.no_follow)
    return 0


def _handle_stack_prod_ps(_: argparse.Namespace) -> int:
    compose_ps(config.PROD_COMPOSE)
    return 0


def _handle_uv_sync_all(_: argparse.Namespace) -> int:
    _handle_uv_platform_sync(argparse.Namespace())
    _handle_uv_docs_sync(argparse.Namespace())
    return 0


def _handle_uv_platform_sync(_: argparse.Namespace) -> int:
    run_command(
        [
            config.UV_BIN,
            "sync",
            "--project",
            "apps/platform",
            "--extra",
            "dev",
            "--frozen",
        ]
    )
    return 0


def _handle_uv_platform_clean(_: argparse.Namespace) -> int:
    run_command(["rm", "-rf", str(config.PLATFORM_VENV_DIR)])
    return 0


def _handle_uv_platform_reset(_: argparse.Namespace) -> int:
    _handle_uv_platform_clean(argparse.Namespace())
    _handle_uv_platform_sync(argparse.Namespace())
    return 0


def _handle_uv_docs_sync(_: argparse.Namespace) -> int:
    run_command(
        [
            config.UV_BIN,
            "sync",
            "--project",
            "packages/docs_tooling",
            "--extra",
            "dev",
            "--frozen",
        ]
    )
    return 0


def _handle_uv_docs_clean(_: argparse.Namespace) -> int:
    run_command(["rm", "-rf", str(config.DOCTOOLS_VENV_DIR)])
    return 0


def _handle_uv_docs_reset(_: argparse.Namespace) -> int:
    _handle_uv_docs_clean(argparse.Namespace())
    _handle_uv_docs_sync(argparse.Namespace())
    return 0


def _handle_uv_cache_clean(_: argparse.Namespace) -> int:
    run_command(["rm", "-rf", ".uv-cache"])
    run_command(["rm", "-rf", ".cache/uv"])
    return 0


def _handle_doctools_build(_: argparse.Namespace) -> int:
    _run_images_build(("docs",))
    return 0


def _handle_doctools_up(_: argparse.Namespace) -> int:
    compose_up(config.DOCS_COMPOSE, [config.DEFAULT_DOCS_SERVICE])
    return 0


def _handle_doctools_down(_: argparse.Namespace) -> int:
    compose_down(config.DOCS_COMPOSE)
    return 0


def _handle_doctools_shell(_: argparse.Namespace) -> int:
    compose_shell(config.DOCS_COMPOSE, config.DEFAULT_DOCS_SERVICE)
    return 0


def _handle_devcontainer_build(_: argparse.Namespace) -> int:
    run_command(compose_command(config.DEVCONTAINER_COMPOSE, "build", config.DEFAULT_DEV_SERVICE))
    return 0


def _handle_devcontainer_up(_: argparse.Namespace) -> int:
    run_command(compose_command(config.DEVCONTAINER_COMPOSE, "up", "-d", config.DEFAULT_DEV_SERVICE))
    return 0


def _handle_devcontainer_down(_: argparse.Namespace) -> int:
    compose_down(config.DEVCONTAINER_COMPOSE)
    return 0


def _handle_devcontainer_shell(_: argparse.Namespace) -> int:
    compose_shell(config.DEVCONTAINER_COMPOSE, config.DEFAULT_DEV_SERVICE)
    return 0


def _handle_docsite_up(args: argparse.Namespace) -> int:
    run_command(["docker", "rm", "-f", config.DOCSITE_CONTAINER], check=False)
    script = (
        "set +u; set -eo pipefail; "
        f"{config.UV_BIN} run --project packages/docs_tooling --extra dev "
        "mkdocs serve --config-file packages/docs_tooling/mkdocs.yml "
        "--dev-addr \"$${DOCSITE_ADDR:-0.0.0.0}:$${DOCSITE_PORT:-8010}\""
    )
    cmd = compose_command(
        config.DOCS_COMPOSE,
        "run",
        "-d",
        "--name",
        config.DOCSITE_CONTAINER,
        "--service-ports",
        "-e",
        f"DOCSITE_ADDR={args.addr}",
        "-e",
        f"DOCSITE_PORT={args.port}",
        config.DEFAULT_DOCS_SERVICE,
        "bash",
        "-c",
        script,
    )
    run_command(cmd, env={"DOCS_DEV_PORT": str(args.port)})
    os.environ["DOCSITE_URL"] = f"http://{args.host}:{args.port}"
    print(f"[docsite] Serving docs at {os.environ['DOCSITE_URL']}")
    return 0


def _handle_docsite_down(_: argparse.Namespace) -> int:
    run_command(["docker", "rm", "-f", config.DOCSITE_CONTAINER], check=False)
    return 0


def _handle_docsite_restart(args: argparse.Namespace) -> int:
    _handle_docsite_down(argparse.Namespace())
    _handle_docsite_up(args)
    return 0


def _handle_docsite_clean(_: argparse.Namespace) -> int:
    _handle_docsite_down(argparse.Namespace())
    _handle_docs_clean(argparse.Namespace())
    return 0


def _handle_docsite_launch(args: argparse.Namespace) -> int:
    url = f"http://{args.host}:{args.port}"
    run_command([
        config.PYTHON_BIN,
        "-c",
        f"import webbrowser; webbrowser.open('{url}')",
    ])
    return 0


def _handle_docsite_preview(_: argparse.Namespace) -> int:
    preview_path = config.DOCSITE_PREVIEW
    if not preview_path.exists():
        raise SystemExit(f"[docsite.preview] missing built site at {preview_path}")
    uri = preview_path.resolve().as_uri()
    run_command(
        [
            config.PYTHON_BIN,
            "-c",
            f"import webbrowser; webbrowser.open('{uri}')",
        ]
    )
    return 0


def _handle_clean_mypy(_: argparse.Namespace) -> int:
    run_command(["rm", "-rf", ".mypy_cache"])
    return 0


def _handle_clean_pyright(_: argparse.Namespace) -> int:
    run_command(["rm", "-rf", ".pyrightcache"])
    return 0


def _handle_clean_pycache(_: argparse.Namespace) -> int:
    for path in (".pytype",):
        run_command(["rm", "-rf", path], check=False)
    run_command(
        [
            config.PYTHON_BIN,
            "-c",
            dedent(
                """
                import pathlib, shutil
                for cache_dir in pathlib.Path('.').rglob('__pycache__'):
                    shutil.rmtree(cache_dir, ignore_errors=True)
                for pyc in pathlib.Path('.').rglob('*.py[co]'):
                    pyc.unlink(missing_ok=True)
                """
            ).strip(),
        ]
    )
    return 0


def _handle_clean_coverage(_: argparse.Namespace) -> int:
    run_command(["rm", "-f", ".coverage"])
    run_command(["rm", "-rf", "htmlcov"])
    return 0


def _handle_clean_all(_: argparse.Namespace) -> int:
    _handle_typewiz_clean(argparse.Namespace())
    _handle_clean_mypy(argparse.Namespace())
    _handle_pytest_clean(argparse.Namespace())
    _handle_clean_pyright(argparse.Namespace())
    _handle_clean_coverage(argparse.Namespace())
    _handle_clean_pycache(argparse.Namespace())
    return 0


def _handle_typewiz_audit(_: argparse.Namespace) -> int:
    _ensure_typewiz_dir()
    uv_run(
        "apps/platform",
        "typewiz",
        "audit",
        "--max-depth",
        "3",
        "--manifest",
        str(TYPEWIZ_MANIFEST),
        "--readiness",
        "--readiness-status",
        "blocked",
        "--readiness-status",
        "ready",
        *TYPEWIZ_PATHS,
        no_sync=True,
    )
    return 0


def _handle_typewiz_dashboard(_: argparse.Namespace) -> int:
    _handle_typewiz_audit(argparse.Namespace())
    uv_run(
        "apps/platform",
        "typewiz",
        "dashboard",
        "--manifest",
        str(TYPEWIZ_MANIFEST),
        "--format",
        "markdown",
        "--output",
        "out/test-reports/typing/dashboard.md",
        no_sync=True,
    )
    uv_run(
        "apps/platform",
        "typewiz",
        "dashboard",
        "--manifest",
        str(TYPEWIZ_MANIFEST),
        "--format",
        "html",
        "--output",
        "out/test-reports/typing/dashboard.html",
        no_sync=True,
    )
    return 0


def _handle_typewiz_readiness(_: argparse.Namespace) -> int:
    _handle_typewiz_audit(argparse.Namespace())
    args = [
        "apps/platform",
        "typewiz",
        "readiness",
        "--manifest",
        str(TYPEWIZ_MANIFEST),
        "--level",
        config.TYPEWIZ_LEVEL,
        "--limit",
        config.TYPEWIZ_LIMIT,
    ]
    for status in config.TYPEWIZ_STATUSES:
        args.extend(["--status", status])
    uv_run(*args, no_sync=True)
    return 0


def _handle_typewiz_clean(_: argparse.Namespace) -> int:
    run_command(["rm", "-rf", ".typewiz_cache"])
    run_command(["rm", "-rf", "out/test-reports/typing"])
    return 0


def _handle_shell_platform(_: argparse.Namespace) -> int:
    compose_shell(config.DEV_COMPOSE, "platform")
    return 0


def _handle_shell_worker(_: argparse.Namespace) -> int:
    compose_shell(config.DEV_COMPOSE, "platform_worker")
    return 0


def _handle_shell_beat(_: argparse.Namespace) -> int:
    compose_shell(config.DEV_COMPOSE, "platform_beat")
    return 0


def _handle_db_psql(_: argparse.Namespace) -> int:
    compose_exec(
        config.DEV_COMPOSE,
        "postgres",
        "bash",
        "-lc",
        'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"',
    )
    return 0


def _handle_keycloak_shell(_: argparse.Namespace) -> int:
    compose_shell(config.DEVCONTAINER_COMPOSE, "keycloak")
    return 0


def _handle_keycloak_psql(_: argparse.Namespace) -> int:
    compose_exec(
        config.DEV_COMPOSE,
        "postgres-keycloak",
        "bash",
        "-lc",
        "psql -U keycloak -d keycloak",
    )
    return 0


def _handle_redis_shell(_: argparse.Namespace) -> int:
    compose_exec(config.DEV_COMPOSE, "redis", "redis-cli")
    return 0


def _handle_redis_ping(_: argparse.Namespace) -> int:
    compose_exec(config.DEV_COMPOSE, "redis", "redis-cli", "-n", "1", "ping")
    return 0


def _handle_images_build(args: argparse.Namespace) -> int:
    _run_images_build(tuple(args.images))
    return 0


def _handle_images_load(args: argparse.Namespace) -> int:
    _run_images_build(tuple(args.images), load=True)
    return 0


def _handle_images_push(args: argparse.Namespace) -> int:
    _run_images_build(tuple(args.images), push=True)
    return 0


def _handle_images_cache_warm(_: argparse.Namespace) -> int:
    flags = config.bake_cache_flags()
    run_command(["docker", "buildx", "bake", *flags, "cache-warm"])
    return 0


def _handle_images_build_prod(args: argparse.Namespace) -> int:
    run_command(compose_command(config.PROD_COMPOSE, "build", *args.images))
    return 0


def _handle_docker_du(_: argparse.Namespace) -> int:
    run_command(["docker", "system", "df"])
    return 0


def _handle_docker_prune(_: argparse.Namespace) -> int:
    run_command(["docker", "container", "prune", "--force"])
    run_command(["docker", "image", "prune", "--all", "--force"])
    run_command(["docker", "network", "prune", "--force"])
    run_command(["docker", "volume", "prune", "--force"])
    return 0


def _handle_docker_reset(_: argparse.Namespace) -> int:
    _handle_docker_compose_reset(argparse.Namespace())
    _handle_docker_prune(argparse.Namespace())
    _handle_buildx_prune(argparse.Namespace())
    _handle_buildx_reset(argparse.Namespace())
    _handle_docker_du(argparse.Namespace())
    return 0


def _handle_docker_context_list(_: argparse.Namespace) -> int:
    run_command(["docker", "context", "ls"])
    return 0


def _handle_docker_context_remove(args: argparse.Namespace) -> int:
    run_command(["docker", "context", "rm", args.name])
    return 0


def _handle_docker_context_clean(_: argparse.Namespace) -> int:
    output = _capture_command(["docker", "context", "ls", "--format", "{{.Name}}"])
    for name in output.splitlines():
        if name.strip() and name.strip() != "default":
            run_command(["docker", "context", "rm", name.strip()])
    return 0


def _handle_docker_containers_list(_: argparse.Namespace) -> int:
    run_command(["docker", "ps", "-a"])
    return 0


def _handle_docker_containers_list_running(_: argparse.Namespace) -> int:
    run_command(["docker", "ps"])
    return 0


def _handle_docker_containers_stop_all(_: argparse.Namespace) -> int:
    ids = _capture_command(["docker", "ps", "-q"]).split()
    if ids:
        run_command(["docker", "stop", *ids])
    return 0


def _handle_docker_containers_remove_all(_: argparse.Namespace) -> int:
    ids = _capture_command(["docker", "ps", "-a", "-q"]).split()
    if ids:
        run_command(["docker", "rm", "-f", *ids])
    return 0


def _handle_docker_containers_prune(_: argparse.Namespace) -> int:
    run_command(["docker", "container", "prune", "--force"])
    return 0


def _handle_docker_containers_reset(_: argparse.Namespace) -> int:
    _handle_docker_containers_stop_all(argparse.Namespace())
    _handle_docker_containers_remove_all(argparse.Namespace())
    return 0


def _handle_docker_images_list(_: argparse.Namespace) -> int:
    run_command(["docker", "images", "-a"])
    return 0


def _handle_docker_images_remove_all(_: argparse.Namespace) -> int:
    ids = _capture_command(["docker", "images", "-a", "-q"]).split()
    if ids:
        run_command(["docker", "rmi", "-f", *ids])
    return 0


def _handle_docker_images_prune(_: argparse.Namespace) -> int:
    run_command(["docker", "image", "prune", "--all", "--force"])
    return 0


def _handle_docker_images_reset(_: argparse.Namespace) -> int:
    _handle_docker_images_remove_all(argparse.Namespace())
    return 0


def _handle_docker_networks_list(_: argparse.Namespace) -> int:
    run_command(["docker", "network", "ls"])
    return 0


def _handle_docker_networks_prune(_: argparse.Namespace) -> int:
    run_command(["docker", "network", "prune", "--force"])
    return 0


def _handle_docker_networks_reset(_: argparse.Namespace) -> int:
    names = _capture_command(["docker", "network", "ls", "--format", "{{.Name}} {{.ID}}"]).splitlines()
    for line in names:
        if not line:
            continue
        name, network_id = line.split()
        if name in {"bridge", "host", "none"}:
            continue
        run_command(["docker", "network", "rm", network_id], check=False)
    return 0


def _handle_docker_volumes_list(_: argparse.Namespace) -> int:
    run_command(["docker", "volume", "ls"])
    return 0


def _handle_docker_volumes_prune(_: argparse.Namespace) -> int:
    run_command(["docker", "volume", "prune", "--force"])
    return 0


def _handle_docker_volumes_reset(_: argparse.Namespace) -> int:
    names = _capture_command(["docker", "volume", "ls", "--format", "{{.Name}}"]).split()
    for name in names:
        run_command(["docker", "volume", "rm", name], check=False)
    return 0


def _handle_docker_compose_ps(_: argparse.Namespace) -> int:
    compose_ps(config.DEV_COMPOSE)
    return 0


def _handle_docker_compose_reset(_: argparse.Namespace) -> int:
    run_command(compose_command(config.DEV_COMPOSE, "down", "--rmi", "all", "--volumes", "--remove-orphans"))
    return 0


def _handle_docker_compose_reset_all(_: argparse.Namespace) -> int:
    _handle_docker_compose_reset(argparse.Namespace())
    _handle_docker_images_prune(argparse.Namespace())
    _handle_docker_volumes_prune(argparse.Namespace())
    _handle_docker_networks_prune(argparse.Namespace())
    return 0


def _handle_buildx_du(_: argparse.Namespace) -> int:
    run_command(["docker", "buildx", "du"], check=False)
    return 0


def _handle_buildx_setup(_: argparse.Namespace) -> int:
    run_command(["./scripts/setup_buildx_builder.sh"])
    return 0


def _handle_buildx_inspect(_: argparse.Namespace) -> int:
    run_command(["docker", "buildx", "inspect", "--bootstrap"])
    return 0


def _handle_buildx_clean(_: argparse.Namespace) -> int:
    run_command(["rm", "-rf", ".docker/buildx-cache"])
    return 0


def _handle_buildx_prune(_: argparse.Namespace) -> int:
    run_command(["docker", "buildx", "prune", "--all", "--force"])
    return 0


def _handle_buildx_reset(_: argparse.Namespace) -> int:
    _handle_buildx_clean(argparse.Namespace())
    _handle_buildx_setup(argparse.Namespace())
    return 0


def _handle_buildx_reset_builders(_: argparse.Namespace) -> int:
    output = _capture_command(["docker", "buildx", "ls"])
    for line in output.splitlines()[1:]:
        name = line.split()[0]
        if name != "default":
            run_command(["docker", "buildx", "rm", name])
    return 0


def _handle_buildx_reset_all(_: argparse.Namespace) -> int:
    _handle_buildx_prune(argparse.Namespace())
    _handle_buildx_clean(argparse.Namespace())
    _handle_buildx_reset_builders(argparse.Namespace())
    return 0


# Additional command registrations are defined below.


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
