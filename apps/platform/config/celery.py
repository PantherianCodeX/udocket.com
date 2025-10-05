from __future__ import annotations

import os
from typing import Any

from celery import Celery


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.getenv("DJANGO_SETTINGS_MODULE", "apps.platform.config.settings.dev"),
)

app = Celery("udocket_platform")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Ensure Celery emits task events without requiring the ``-E`` CLI flag so
# monitoring UIs (and our websocket hooks) can receive state changes even when
# the worker command is wrapped by docker compose watch tooling.
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True
app.conf.worker_hijack_root_logger = False


@app.task(bind=True)
def ping(self: Any) -> str:  # pragma: no cover - trivial
    return "pong"
