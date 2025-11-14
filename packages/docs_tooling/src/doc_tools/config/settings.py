from __future__ import annotations

# pyright: strict

"""Environment-backed settings for doc_tools."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from packages.common.env import load_env_defaults
from packages.common.repo import REPO_ROOT

PACKAGE_ROOT = Path(__file__).resolve().parents[3]

load_env_defaults(
    env_var="DOCS_TOOLING_ENV_FILE",
    default_paths=(
        PACKAGE_ROOT / ".env",
        REPO_ROOT / ".env",
    ),
)


class DocToolsSettings(BaseSettings):
    """Environment configuration for the documentation tooling package."""

    model_config = SettingsConfigDict(env_prefix="DOCS_TOOLING_", extra="ignore")

    repo_root: Path | None = Field(default=None, alias="REPO_ROOT")
    package_root: Path | None = Field(default=None, alias="PACKAGE_ROOT")
    docs_root: Path | None = Field(default=None, alias="ROOT")
    config_root: Path | None = Field(default=None, alias="CONFIG_ROOT")
    build_root: Path | None = Field(default=None, alias="BUILD_ROOT")
    doc_builds_root: Path | None = Field(default=None, alias="DOC_BUILDS_ROOT")
    diagram_index_path: Path | None = Field(default=None, alias="DIAGRAM_INDEX_PATH")


def _expand(path: Path | None, default: Path) -> Path:
    return path.expanduser() if path else default


def resolve_package_root(cfg: DocToolsSettings | None = None) -> Path:
    settings = cfg or doc_tools_settings
    base = _expand(settings.package_root, PACKAGE_ROOT)
    return base


def resolve_docs_root(cfg: DocToolsSettings | None = None) -> Path:
    settings = cfg or doc_tools_settings
    return _expand(settings.docs_root, REPO_ROOT / "docs")


def resolve_config_root(cfg: DocToolsSettings | None = None) -> Path:
    settings = cfg or doc_tools_settings
    return _expand(settings.config_root, PACKAGE_ROOT / "config")


def resolve_build_root(cfg: DocToolsSettings | None = None) -> Path:
    settings = cfg or doc_tools_settings
    return _expand(settings.build_root, PACKAGE_ROOT / "build")


def resolve_doc_builds_root(cfg: DocToolsSettings | None = None) -> Path:
    settings = cfg or doc_tools_settings
    return _expand(settings.doc_builds_root, REPO_ROOT / "out" / "doc-builds")


def resolve_diagram_index_path(cfg: DocToolsSettings | None = None) -> Path:
    settings = cfg or doc_tools_settings
    docs_root = resolve_docs_root(settings)
    default = docs_root / "overview" / "tdd" / "appendices" / "diagrams.md"
    return _expand(settings.diagram_index_path, default)


def resolve_repo_root(_: DocToolsSettings | None = None) -> Path:
    return REPO_ROOT


doc_tools_settings = DocToolsSettings()


__all__ = [
    "DocToolsSettings",
    "doc_tools_settings",
    "resolve_build_root",
    "resolve_config_root",
    "resolve_diagram_index_path",
    "resolve_doc_builds_root",
    "resolve_docs_root",
    "resolve_package_root",
    "resolve_repo_root",
]
