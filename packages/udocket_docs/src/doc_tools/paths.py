"""Backward-compatible re-export of path helpers."""

from __future__ import annotations

from doc_tools.config.paths import (  # noqa: F401
    ALL_TEMPLATE_ROOTS,
    AREA_PREFIXES,
    CONFIG_PATH,
    CONFIG_ROOT,
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
    "REPO_ROOT",
    "DOCS_PACKAGE_ROOT",
    "DOCS_ROOT",
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
