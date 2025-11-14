"""Backward-compatible re-export of path helpers."""

from __future__ import annotations

from doc_tools.config.paths import (
    ALL_TEMPLATE_ROOTS,
    AREA_PREFIXES,
    CONFIG_PATH,
    CONFIG_ROOT,
    DIAGRAM_INDEX_PATH,
    DOCS_PACKAGE_ROOT,
    DOCS_ROOT,
    DOC_BUILDS_ROOT,
    PDF_DEV_DIR,
    PDF_OUTPUT_ROOT,
    REPO_ROOT,
    SERVICE_AREAS,
    SERVICE_ROOTS,
    SITE_DEV_DIR,
    SITE_OUTPUT_ROOT,
    BUILD_ROOT,
    area_path,
    load_service_areas,
)

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
