"""Helper utilities for the uDocket CLI commands."""

from __future__ import annotations

import shlex
from typing import Iterable, Sequence

from . import config
from .runner import run_command, shlex_join


def compose_command( compose: config.ComposeConfig, *args: str, project: str | None = None) -> list[str]:
    return config.compose_argv(compose, *args, project=project or config.DEFAULT_PROJECT)


def compose_run(
    compose: config.ComposeConfig,
    service: str,
    command: Sequence[str],
    *,
    env: dict[str, str] | None = None,
    project: str | None = None,
) -> None:
    argv = compose_command(
        compose,
        "run",
        "--rm",
        service,
        *command,
        project=project,
    )
    run_command(argv, env=env)


def compose_exec(
    compose: config.ComposeConfig,
    service: str,
    *command: str,
    project: str | None = None,
) -> None:
    argv = compose_command(compose, "exec", service, *command, project=project)
    run_command(argv)


def compose_shell(compose: config.ComposeConfig, service: str) -> None:
    compose_exec(compose, service, "bash", "-l")


def compose_up(
    compose: config.ComposeConfig,
    services: Sequence[str] | None = None,
    *,
    detach: bool = True,
    project: str | None = None,
) -> None:
    args = ["up"]
    if detach:
        args.append("-d")
    if services:
        args.extend(services)
    run_command(compose_command(compose, *args, project=project))


def compose_down(compose: config.ComposeConfig, *, project: str | None = None) -> None:
    run_command(compose_command(compose, "down", project=project))


def compose_logs(
    compose: config.ComposeConfig,
    services: Sequence[str] | None = None,
    *,
    follow: bool = True,
    project: str | None = None,
) -> None:
    args = ["logs"]
    if follow:
        args.append("-f")
    if services:
        args.extend(services)
    run_command(compose_command(compose, *args, project=project))


def compose_ps(compose: config.ComposeConfig, *, project: str | None = None) -> None:
    run_command(compose_command(compose, "ps", project=project))


def compose_restart(
    compose: config.ComposeConfig,
    services: Sequence[str] | None = None,
    *,
    project: str | None = None,
) -> None:
    args = ["restart"]
    if services:
        args.extend(services)
    run_command(compose_command(compose, *args, project=project))


def docs_shell_script(script: str) -> str:
    return "set -euo pipefail; " + script


def docs_run_bash(script: str) -> None:
    compose_run(
        config.DOCS_COMPOSE,
        config.DEFAULT_DOCS_SERVICE,
        ("bash", "-c", docs_shell_script(script)),
    )


def ensure_services(services: Iterable[str] | None, default: Sequence[str]) -> list[str]:
    return list(services or default)


def quote(value: str) -> str:
    return shlex.quote(value)


def uv_run(
    project: str,
    *args: str,
    extras: Sequence[str] | None = None,
    no_sync: bool = False,
) -> None:
    argv = [config.UV_BIN, "run", "--project", project]
    if extras:
        for extra in extras:
            argv.extend(["--extra", extra])
    if no_sync:
        argv.append("--no-sync")
    argv.extend(args)
    run_command(argv)


def uv_run_platform(*args: str, extras: Sequence[str] | None = None) -> None:
    uv_run("apps/platform", *args, extras=extras or ("dev",))


def uv_run_docs(*args: str, extras: Sequence[str] | None = None) -> None:
    uv_run("packages/docs_tooling", *args, extras=extras or ("dev",))


def docs_manage_docs(*args: str) -> None:
    command = [
        config.UV_BIN,
        "run",
        "--project",
        "packages/docs_tooling",
        "--extra",
        "dev",
        "python",
        "-m",
        "doc_tools.manage_docs",
        *args,
    ]
    script = shlex_join(command)
    docs_run_bash(script)


def docs_module(module: str, *module_args: str) -> None:
    command = [
        config.UV_BIN,
        "run",
        "--project",
        "packages/docs_tooling",
        "--extra",
        "dev",
        "python",
        "-m",
        module,
        *module_args,
    ]
    docs_run_bash(shlex_join(command))


def docs_run_pytest(pytest_args: Sequence[str], *, coverage: bool = False) -> None:
    args_literal = " ".join(pytest_args)
    env_assignment = f"DOCS_PYTEST_ARGS={quote(args_literal)} " if args_literal else ""
    command = (
        f"{env_assignment}{config.UV_BIN} run --project packages/docs_tooling --extra dev "
        "python -m doc_tools.pytest_runner"
    )
    if coverage:
        command += " --coverage"
    docs_run_bash(command)
