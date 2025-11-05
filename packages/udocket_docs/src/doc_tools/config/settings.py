from __future__ import annotations

# pyright: strict

"""Environment-backed settings for doc_tools."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from packages.udocket_common.env import load_env_defaults

_PACKAGE_ROOT = Path(__file__).resolve().parents[3]
_REPO_ROOT = _PACKAGE_ROOT.parents[1]

load_env_defaults(
    env_var="UDOCKET_DOCS_ENV_FILE",
    default_paths=(
        _PACKAGE_ROOT / ".env",
        _REPO_ROOT / ".env",
    ),
)


class DocToolsSettings(BaseSettings):
    """Environment configuration for the documentation tooling package."""

    model_config = SettingsConfigDict(env_prefix="UDOCKET_DOCS_", extra="ignore")

    repo_root: Optional[Path] = Field(default=None, alias="REPO_ROOT")
    package_root: Optional[Path] = Field(default=None, alias="PACKAGE_ROOT")
    docs_root: Optional[Path] = Field(default=None, alias="ROOT")
    config_root: Optional[Path] = Field(default=None, alias="CONFIG_ROOT")
    build_root: Optional[Path] = Field(default=None, alias="BUILD_ROOT")
    doc_builds_root: Optional[Path] = Field(default=None, alias="DOC_BUILDS_ROOT")
    diagram_index_path: Optional[Path] = Field(default=None, alias="DIAGRAM_INDEX_PATH")


def _expand(path: Optional[Path], default: Path) -> Path:
    return path.expanduser() if path else default


def _is_repo_root(candidate: Path) -> bool:
    return (candidate / "docs").exists() and (candidate / "packages").exists()


def _detect_repo_root(default: Path) -> Path:
    if _is_repo_root(default):
        return default
    for parent in default.parents:
        if _is_repo_root(parent):
            return parent
    return default


def resolve_repo_root(cfg: DocToolsSettings | None = None) -> Path:
    settings = cfg or doc_tools_settings
    if settings.repo_root is not None:
        return settings.repo_root.expanduser()
    return _detect_repo_root(_REPO_ROOT)


def resolve_package_root(cfg: DocToolsSettings | None = None) -> Path:
    settings = cfg or doc_tools_settings
    base = _expand(settings.package_root, _PACKAGE_ROOT)
    return base


def resolve_docs_root(cfg: DocToolsSettings | None = None) -> Path:
    settings = cfg or doc_tools_settings
    repo_root = resolve_repo_root(settings)
    default = repo_root / "docs"
    return _expand(settings.docs_root, default)


def resolve_config_root(cfg: DocToolsSettings | None = None) -> Path:
    settings = cfg or doc_tools_settings
    package_root = resolve_package_root(settings)
    default = package_root / "config"
    return _expand(settings.config_root, default)


def resolve_build_root(cfg: DocToolsSettings | None = None) -> Path:
    settings = cfg or doc_tools_settings
    package_root = resolve_package_root(settings)
    default = package_root / "build"
    return _expand(settings.build_root, default)


def resolve_doc_builds_root(cfg: DocToolsSettings | None = None) -> Path:
    settings = cfg or doc_tools_settings
    repo_root = resolve_repo_root(settings)
    default = repo_root / "doc-builds"
    return _expand(settings.doc_builds_root, default)


def resolve_diagram_index_path(cfg: DocToolsSettings | None = None) -> Path:
    settings = cfg or doc_tools_settings
    docs_root = resolve_docs_root(settings)
    default = docs_root / "overview" / "tdd" / "appendices" / "diagrams.md"
    return _expand(settings.diagram_index_path, default)


doc_tools_settings = DocToolsSettings()


__all__ = [
    "DocToolsSettings",
    "doc_tools_settings",
    "resolve_repo_root",
    "resolve_package_root",
    "resolve_docs_root",
    "resolve_config_root",
    "resolve_build_root",
    "resolve_doc_builds_root",
    "resolve_diagram_index_path",
]
