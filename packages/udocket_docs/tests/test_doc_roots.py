from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def _reload_with_config(tmp_path: Path, content: str | None) -> object:
    path = tmp_path / "docs" / "config" / "docs_config.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    if content is not None:
        path.write_text(content, encoding="utf-8")
    else:
        if path.exists():
            path.unlink()

    import docs.tools.doc_roots as doc_roots

    doc_roots = importlib.reload(doc_roots)
    doc_roots.CONFIG_PATH = path
    doc_roots.DOCS_SRC = tmp_path / "docs" / "src"
    doc_roots.SERVICE_AREAS = doc_roots._load_service_areas()
    doc_roots.AREA_PREFIXES = doc_roots.SERVICE_AREAS
    doc_roots.SERVICE_ROOTS = [doc_roots.area_path(area) for area in doc_roots.SERVICE_AREAS]
    return doc_roots


def test_load_service_areas_defaults(tmp_path: Path) -> None:
    module = _reload_with_config(tmp_path, None)
    assert module.SERVICE_AREAS == ("platform", "automation", "data", "customer", "experience")


def test_load_service_areas_from_config(tmp_path: Path) -> None:
    module = _reload_with_config(tmp_path, "service_areas:\n  - platform\n  - data\n  - automation\n")
    assert module.SERVICE_AREAS == ("platform", "data", "automation")
    assert module.area_path("platform") == tmp_path / "docs" / "src" / "platform"


def test_load_service_areas_invalid(tmp_path: Path) -> None:
    module = _reload_with_config(tmp_path, "service_areas: invalid")
    assert module.SERVICE_AREAS == ("platform", "automation", "data", "customer", "experience")
