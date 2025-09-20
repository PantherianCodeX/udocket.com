from django.apps import AppConfig


class CasesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.platform.cases"
    label = "cases"

    def ready(self):  # pragma: no cover - signal wiring
        from . import signals  # noqa: F401
