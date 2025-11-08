from __future__ import annotations

import os
try:
    import django
except ImportError:  # pragma: no cover - django-free environments
    django = None


def pytest_configure() -> None:
    """Ensure Django settings are available for any test invocation."""

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.platform.config.settings.dev")
    if django is not None:
        django.setup()
