from pathlib import Path

from django.apps import AppConfig


class JobsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.platform.jobs"
    label = "jobs"
    # Ensure Django resolves this app to a single filesystem path even when
    # type stubs exist under a parallel "typings/apps/platform/jobs" tree.
    path = str(Path(__file__).resolve().parent)
