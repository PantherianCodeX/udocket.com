"""Configuration helpers shared by the uDocket CLI commands."""

from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Sequence
from collections.abc import Iterable

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
DEFAULT_PROJECT: Final[str] = os.environ.get("PROJECT_NAME", "udocket")
PYTHON_BIN: Final[str] = os.environ.get("PYTHON", "python")
UV_BIN: Final[str] = os.environ.get("UV", "uv")
DEFAULT_DOCS_SERVICE: Final[str] = "docs"
DEFAULT_DEV_SERVICE: Final[str] = "platform-dev"
DEFAULT_STACK_SERVICES: Final[tuple[str, ...]] = (
    "platform",
    "platform_worker",
    "platform_beat",
    "redis",
    "postgres",
    "postgres-keycloak",
    "keycloak",
)
DEFAULT_SERVICE: Final[str] = os.environ.get("SERVICE", "platform")
STACK_SERVICES_ENV = os.environ.get("SERVICES")
STACK_SERVICES: Final[tuple[str, ...]] = (
    tuple(STACK_SERVICES_ENV.split()) if STACK_SERVICES_ENV else DEFAULT_STACK_SERVICES
)


def _detect_cpu_count() -> int:
    env_override = os.environ.get("HOST_CPUS")
    if env_override:
        with contextlib.suppress(ValueError):
            return int(env_override)
    try:
        cpu_count = os.cpu_count()
    except NotImplementedError:  # pragma: no cover - platform fallback
        cpu_count = None
    return cpu_count or 4


HOST_CPUS: Final[int] = _detect_cpu_count()
JOBS: Final[int] = int(os.environ.get("JOBS", str(HOST_CPUS)))


@dataclass(frozen=True)
class ComposeConfig:
    files: tuple[Path, ...]

    @property
    def file_flags(self) -> tuple[str, ...]:
        return tuple(str(path) for path in self.files)

    def add(self, *seqs: Iterable[Path]) -> ComposeConfig:
        """
        Construct a ComposeConfig by concatenating the provided sequences,
        removing duplicates while preserving first-seen order.
        """
        seen: dict[str, Path] = {}
        # start with the instance's own files first (preserve their precedence)
        for p in self.files:
            key = str(p)
            if key not in seen:
                seen[key] = p

        # then add provided sequences
        for seq in seqs:
            if not seq:
                continue
            for p in seq:
                key = str(p)  # use string representation as stable key
                if key not in seen:
                    seen[key] = p
        return ComposeConfig(files=tuple(seen.values()))


def _files(*names: str) -> tuple[Path, ...]:
    return tuple(REPO_ROOT / name for name in names)


def compose_base(*extra: str) -> ComposeConfig:
    return ComposeConfig(files=_files(*extra))


BASE_COMPOSE = ComposeConfig(files=_files("docker-compose.yml"))
DEV_COMPOSE = BASE_COMPOSE.add(_files("docker-compose.dev.yml"))
PROD_COMPOSE = BASE_COMPOSE.add(_files("docker-compose.prod.yml"))
CACHE_COMPOSE = BASE_COMPOSE.add(_files("docker-compose.cache.yml"))
DEVCONTAINER_COMPOSE = BASE_COMPOSE.add(
    DEV_COMPOSE.files, CACHE_COMPOSE.files, _files(".devcontainer/docker-compose.devcontainer.yml")
)
DOCS_COMPOSE = BASE_COMPOSE.add(DEV_COMPOSE.files, CACHE_COMPOSE.files)


DEFAULT_DOCKER_ENV: Final[dict[str, str]] = {
    "PROJECT_NAME": DEFAULT_PROJECT,
}

PLATFORM_IMAGE: Final[str] = "udocket-platform"
DOCS_IMAGE: Final[str] = "udocket-docs-toolbox"
KEYCLOAK_IMAGE: Final[str] = "udocket-keycloak"

USE_BUILD: Final[bool] = os.environ.get("USE_BUILD", "1") == "1"
PLATFORMS: Final[str] = os.environ.get("PLATFORMS", "linux/amd64")
PROGRESS: Final[str] = os.environ.get("PROGRESS", "plain")
TAG: Final[str] = os.environ.get("TAG", "dev")
LOCAL_TAG: Final[str] = os.environ.get("LOCAL_TAG", "dev")
AUTO_PUSH: Final[bool] = os.environ.get("AUTO_PUSH", "1") == "1"
RELEASE_PATTERN: Final[str] = os.environ.get("RELEASE_PATTERN", r"^v[0-9]")
SKIP_PUSH: Final[bool] = os.environ.get("SKIP_PUSH", "0") == "1"
LOAD_IMAGES: Final[bool] = os.environ.get("LOAD", "0") == "1"
EXPLICIT_PUSH = os.environ.get("PUSH")
REGISTRY: Final[str | None] = os.environ.get("REGISTRY", "ghcr.io/udocket") or None
IMAGES: Final[tuple[str, ...]] = tuple(
    (os.environ.get("IMAGES") or "platform docs keycloak").split()
)


def should_push() -> bool:
    if SKIP_PUSH:
        return False
    if EXPLICIT_PUSH:
        return EXPLICIT_PUSH != "0"
    if not AUTO_PUSH:
        return False
    import re

    return re.search(RELEASE_PATTERN, TAG) is not None


DO_PUSH: Final[bool] = should_push()
DO_LOAD: Final[bool] = LOAD_IMAGES or bool(os.environ.get("DO_LOAD") == "1")


def buildx_tag_flags(target: str, tags: Sequence[str]) -> list[str]:
    if not tags:
        return []
    first, *rest = tags
    flags = ["--set", f"{target}.tags={first}"]
    for tag in rest:
        flags.extend(["--set", f"{target}.tags+={tag}"])
    return flags


def image_tags(image: str) -> list[str]:
    tags = [f"{image}:{LOCAL_TAG}"]
    if REGISTRY:
        tags.append(f"{REGISTRY}/{image}:{TAG}")
    return tags


PLATFORM_TAGS = image_tags(PLATFORM_IMAGE)
DOCS_TAGS = image_tags(DOCS_IMAGE)
KEYCLOAK_TAGS = image_tags(KEYCLOAK_IMAGE)

BAKE_FILES: Final[tuple[str, ...]] = ("-f", "bake.hcl")


def bake_image_flags(*, load: bool | None = None, push: bool | None = None) -> list[str]:
    flags: list[str] = [*BAKE_FILES, f"--progress={PROGRESS}", "--set", f"*.platform={PLATFORMS}"]
    flags.extend(buildx_tag_flags("platform", PLATFORM_TAGS))
    flags.extend(buildx_tag_flags("docs", DOCS_TAGS))
    flags.extend(buildx_tag_flags("keycloak", KEYCLOAK_TAGS))
    if load if load is not None else DO_LOAD:
        flags.append("--load")
    if push if push is not None else DO_PUSH:
        flags.append("--push")
    extra = os.environ.get("BAKE_EXTRA_FLAGS")
    if extra:
        flags.extend(extra.split())
    return flags


def bake_cache_flags() -> list[str]:
    flags: list[str] = [*BAKE_FILES, f"--progress={PROGRESS}", "--set", f"*.platform={PLATFORMS}"]
    extra = os.environ.get("BAKE_EXTRA_FLAGS")
    if extra:
        flags.extend(extra.split())
    return flags


@dataclass(frozen=True)
class DockerCommand:
    compose: ComposeConfig
    subcommand: Sequence[str]

    def to_argv(self, *, project: str = DEFAULT_PROJECT) -> list[str]:
        return compose_argv(self.compose, *self.subcommand, project=project)


def compose_argv(
    compose: ComposeConfig,
    *subcommand: str,
    project: str = DEFAULT_PROJECT,
) -> list[str]:
    argv = ["docker", "compose", "-p", project]
    for path in compose.files:
        argv.extend(["-f", str(path)])
    argv.extend(subcommand)
    return argv


TYPEWIZ_STATUSES = tuple((os.environ.get("TYPEWIZ_STATUSES", "blocked ready").split()))
TYPEWIZ_LEVEL = os.environ.get("TYPEWIZ_LEVEL", "folder")
TYPEWIZ_LIMIT = os.environ.get("TYPEWIZ_LIMIT", "20")

DOCSITE_CONTAINER = os.environ.get("DOCSITE_CONTAINER", "udocket-docs-site")
DOCSITE_ADDR = os.environ.get("DOCSITE_ADDR", "0.0.0.0")
DOCSITE_HOST = os.environ.get("DOCSITE_HOST", "localhost")
DOCSITE_PORT = int(os.environ.get("DOCSITE_PORT", "8010"))
DOCSITE_URL = os.environ.get("DOCSITE_URL") or f"http://{DOCSITE_HOST}:{DOCSITE_PORT}"
DOCSITE_PREVIEW = Path(os.environ.get("DOCSITE_PREVIEW", "out/doc-builds/sites/dev/index.html"))

PLATFORM_VENV_DIR = Path(os.environ.get("PLATFORM_VENV_DIR", ".venv"))
DOCTOOLS_VENV_DIR = Path(os.environ.get("DOCTOOLS_VENV_DIR", "packages/docs_tooling/.venv"))
