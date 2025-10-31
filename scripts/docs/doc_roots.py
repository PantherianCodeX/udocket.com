"""Shared documentation root configuration."""

from __future__ import annotations

from pathlib import Path

DOCS_SRC = Path("docs/src")

SERVICE_AREAS: tuple[str, ...] = ("platform", "automation", "data", "customer", "experience")
AREA_PREFIXES: tuple[str, ...] = SERVICE_AREAS


def area_path(area: str) -> Path:
    return DOCS_SRC / area


SERVICE_ROOTS = [area_path(area) for area in SERVICE_AREAS]
ALL_TEMPLATE_ROOTS = SERVICE_ROOTS
