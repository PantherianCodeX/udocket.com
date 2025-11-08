from pathlib import Path

from django.apps import AppConfig


class CasesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.platform.cases"
    label = "cases"
    # Mirror jobs app: avoid multiple filesystem locations when stubs are present
    path = str(Path(__file__).resolve().parent)

    def ready(self):  # pragma: no cover - signal wiring
        from . import signals  # noqa: F401
