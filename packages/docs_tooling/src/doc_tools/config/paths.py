from __future__ import annotations

# pyright: strict

"""Path helpers backed by doc_tools settings."""

from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence, cast

import yaml

from .settings import (
    resolve_build_root,
    resolve_config_root,
    resolve_doc_builds_root,
    resolve_docs_root,
    resolve_package_root,
    resolve_repo_root,
    resolve_diagram_index_path,
)


REPO_ROOT = resolve_repo_root()
DOCS_PACKAGE_ROOT = resolve_package_root()
DOCS_ROOT = resolve_docs_root()
CONFIG_ROOT = resolve_config_root()
BUILD_ROOT = resolve_build_root()
DOC_BUILDS_ROOT = resolve_doc_builds_root()
SITE_OUTPUT_ROOT = DOC_BUILDS_ROOT / "sites"
PDF_OUTPUT_ROOT = DOC_BUILDS_ROOT / "pdf"
SITE_DEV_DIR = SITE_OUTPUT_ROOT / "dev"
PDF_DEV_DIR = PDF_OUTPUT_ROOT / "dev"
DIAGRAM_INDEX_PATH = resolve_diagram_index_path()

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

