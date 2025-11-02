from __future__ import annotations

from pathlib import Path

import pytest

from doc_tools import paths


DEFAULT_SERVICE_AREAS = ("platform", "automation", "data", "customer", "experience")


@pytest.fixture(autouse=True)
def reset_cache() -> None:
    paths.load_service_areas.cache_clear()
    yield
    paths.load_service_areas.cache_clear()


def test_load_service_areas_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths, "CONFIG_PATH", tmp_path / "docs_config.yaml", raising=False)
    assert paths.load_service_areas() == DEFAULT_SERVICE_AREAS


def test_load_service_areas_custom(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "docs_config.yaml"
    config.write_text("service_areas:\n  - alpha\n  - bravo\n", encoding="utf-8")
    monkeypatch.setattr(paths, "CONFIG_PATH", config, raising=False)
    assert paths.load_service_areas() == ("alpha", "bravo")


def test_area_path_returns_docs_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths, "DOCS_ROOT", tmp_path / "docs", raising=False)
    result = paths.area_path("platform")
    assert result == tmp_path / "docs" / "platform"
