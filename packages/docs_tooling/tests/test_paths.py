from __future__ import annotations

from pathlib import Path

import pytest

from doc_tools.config import paths
from doc_tools.config import paths as config_paths


DEFAULT_SERVICE_AREAS = ("platform", "automation", "data", "customer", "experience")


@pytest.fixture(autouse=True)
def reset_cache() -> None:
    paths.load_service_areas.cache_clear()
    yield
    paths.load_service_areas.cache_clear()


def test_load_service_areas_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = tmp_path / "docs_config.yaml"
    monkeypatch.setattr(config_paths, "CONFIG_PATH", config_file, raising=False)
    monkeypatch.setattr(paths, "CONFIG_PATH", config_file, raising=False)
    assert paths.load_service_areas() == DEFAULT_SERVICE_AREAS


def test_load_service_areas_custom(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "docs_config.yaml"
    config.write_text("service_areas:\n  - alpha\n  - bravo\n", encoding="utf-8")
    monkeypatch.setattr(config_paths, "CONFIG_PATH", config, raising=False)
    monkeypatch.setattr(paths, "CONFIG_PATH", config, raising=False)
    assert paths.load_service_areas() == ("alpha", "bravo")


def test_area_path_returns_docs_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "docs"
    monkeypatch.setattr(config_paths, "DOCS_ROOT", root, raising=False)
    monkeypatch.setattr(paths, "DOCS_ROOT", root, raising=False)
    result = paths.area_path("platform")
    assert result == tmp_path / "docs" / "platform"
