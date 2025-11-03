from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence, cast

import yaml

_REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[2]


def _expanded(value: str | None, default: Path) -> Path:
    if value is None or not value.strip():
        return default
    return Path(value).expanduser()


def _is_repo_root(candidate: Path) -> bool:
    return (candidate / "docs").exists() and (candidate / "packages").exists()


def _detect_repo_root(default: Path) -> Path:
    if _is_repo_root(default):
        return default
    for parent in default.parents:
        if _is_repo_root(parent):
            return parent
    return default


REPO_ROOT = _expanded(os.getenv("UDOCKET_REPO_ROOT"), _detect_repo_root(_REPO_ROOT_DEFAULT))
DOCS_PACKAGE_ROOT = _expanded(
    os.getenv("UDOCKET_DOCS_PACKAGE_ROOT"), REPO_ROOT / "packages" / "udocket_docs"
)
DOCS_ROOT = _expanded(os.getenv("UDOCKET_DOCS_ROOT"), REPO_ROOT / "docs")
CONFIG_ROOT = _expanded(os.getenv("UDOCKET_DOCS_CONFIG_ROOT"), DOCS_PACKAGE_ROOT / "config")
BUILD_ROOT = _expanded(os.getenv("UDOCKET_DOCS_BUILD_ROOT"), DOCS_PACKAGE_ROOT / "build")
DOC_BUILDS_ROOT = _expanded(os.getenv("UDOCKET_DOC_BUILDS_ROOT"), REPO_ROOT / "doc-builds")
SITE_OUTPUT_ROOT = DOC_BUILDS_ROOT / "sites"
PDF_OUTPUT_ROOT = DOC_BUILDS_ROOT / "pdf"
SITE_DEV_DIR = SITE_OUTPUT_ROOT / "dev"
PDF_DEV_DIR = PDF_OUTPUT_ROOT / "dev"
DIAGRAM_INDEX_PATH = DOCS_ROOT / "overview" / "tdd" / "appendices" / "diagrams.md"

CONFIG_PATH = CONFIG_ROOT / "docs_config.yaml"
_DEFAULT_SERVICE_AREAS: Sequence[str] = (
    "platform",
    "automation",
    "data",
    "customer",
    "experience",
)


@lru_cache(maxsize=1)
def load_service_areas(config_path: Path | None = None) -> tuple[str, ...]:
    if config_path is None:
        config_path = CONFIG_PATH
    if not config_path.exists():
        return tuple(_DEFAULT_SERVICE_AREAS)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return tuple(_DEFAULT_SERVICE_AREAS)
    data = cast(dict[str, Any], raw)
    areas_obj = data.get("service_areas", _DEFAULT_SERVICE_AREAS)
    if not isinstance(areas_obj, list):
        return tuple(_DEFAULT_SERVICE_AREAS)
    cleaned: list[str] = []
    typed_list = cast(list[Any], areas_obj)
    for item in typed_list:
        if not isinstance(item, str):
            return tuple(_DEFAULT_SERVICE_AREAS)
        trimmed = item.strip()
        if trimmed:
            cleaned.append(trimmed)
    return tuple(cleaned) if cleaned else tuple(_DEFAULT_SERVICE_AREAS)


SERVICE_AREAS = load_service_areas()
AREA_PREFIXES: tuple[str, ...] = SERVICE_AREAS
SERVICE_ROOTS = [DOCS_ROOT / area for area in SERVICE_AREAS]
ALL_TEMPLATE_ROOTS = SERVICE_ROOTS


def area_path(area: str) -> Path:
    return DOCS_ROOT / area


__all__ = [
    "REPO_ROOT",
    "DOCS_PACKAGE_ROOT",
    "DOCS_ROOT",
    "DIAGRAM_INDEX_PATH",
    "CONFIG_ROOT",
    "BUILD_ROOT",
    "DOC_BUILDS_ROOT",
    "SITE_OUTPUT_ROOT",
    "PDF_OUTPUT_ROOT",
    "SITE_DEV_DIR",
    "PDF_DEV_DIR",
    "CONFIG_PATH",
    "SERVICE_AREAS",
    "AREA_PREFIXES",
    "SERVICE_ROOTS",
    "ALL_TEMPLATE_ROOTS",
    "area_path",
    "load_service_areas",
]
