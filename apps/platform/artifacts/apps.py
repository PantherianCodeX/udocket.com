from django.apps import AppConfig


class ArtifactsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.platform.artifacts"
    label = "artifacts"

    def ready(self) -> None:  # pragma: no cover - import side effects
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
