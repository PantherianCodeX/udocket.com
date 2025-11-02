from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.fixture
def settings() -> SimpleNamespace:
    """Provide a lightweight stand-in for pytest-django's settings fixture."""
    return SimpleNamespace()
