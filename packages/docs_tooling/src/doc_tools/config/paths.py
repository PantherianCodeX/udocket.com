from __future__ import annotations

# pyright: strict

"""Path helpers backed by doc_tools settings."""

from collections.abc import Sequence
from functools import lru_cache
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pathlib import Path

import yaml

from packages.common.repo import REPO_ROOT

from .settings import (
    resolve_build_root,
    resolve_config_root,
    resolve_diagram_index_path,
    resolve_doc_builds_root,
    resolve_docs_root,
    resolve_package_root,
)

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
    # Coerce to a mapping with "object" values to avoid Any.
    data = cast("dict[str, object]", raw)
    areas_obj = cast("list[str]", data.get("service_areas", _DEFAULT_SERVICE_AREAS))
    cleaned: list[str] = []
    for item in areas_obj:
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
    "ALL_TEMPLATE_ROOTS",
    "AREA_PREFIXES",
    "BUILD_ROOT",
    "CONFIG_PATH",
    "CONFIG_ROOT",
    "DIAGRAM_INDEX_PATH",
    "DOCS_PACKAGE_ROOT",
    "DOCS_ROOT",
    "DOC_BUILDS_ROOT",
    "PDF_DEV_DIR",
    "PDF_OUTPUT_ROOT",
    "REPO_ROOT",
    "SERVICE_AREAS",
    "SERVICE_ROOTS",
    "SITE_DEV_DIR",
    "SITE_OUTPUT_ROOT",
    "area_path",
    "load_service_areas",
]
