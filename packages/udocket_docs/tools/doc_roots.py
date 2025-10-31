"""Shared documentation root configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence, cast

import yaml

DOCS_SRC = Path("docs/src")
CONFIG_PATH = Path("docs/config/docs_config.yaml")
_DEFAULT_SERVICE_AREAS: Sequence[str] = ("platform", "automation", "data", "customer", "experience")


def _load_service_areas() -> tuple[str, ...]:
    if not CONFIG_PATH.exists():
        return tuple(_DEFAULT_SERVICE_AREAS)
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
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


SERVICE_AREAS = _load_service_areas()
AREA_PREFIXES: tuple[str, ...] = SERVICE_AREAS


def area_path(area: str) -> Path:
    return DOCS_SRC / area


SERVICE_ROOTS = [area_path(area) for area in SERVICE_AREAS]
ALL_TEMPLATE_ROOTS = SERVICE_ROOTS
