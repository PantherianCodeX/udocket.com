from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _temp_storage_root(tmp_path_factory: pytest.TempPathFactory, settings) -> Path:
    """Route storage writes to an isolated, writable directory for each test."""
    root = tmp_path_factory.mktemp("storage_root")
    media_root = root / "media"
    media_root.mkdir(parents=True, exist_ok=True)
    settings.STORAGE_ROOT = str(root)
    settings.MEDIA_ROOT = str(media_root)
    return root
