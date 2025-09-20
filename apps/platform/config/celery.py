from __future__ import annotations

import os
from celery import Celery


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.getenv("DJANGO_SETTINGS_MODULE", "apps.platform.config.settings.dev"),
)

app = Celery("udocket_platform")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def ping(self):  # pragma: no cover - trivial
    return "pong"

