from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.platform.accounts"
    label = "accounts"

    def ready(self) -> None:  # type: ignore[override]
        from . import signals  # noqa: F401
