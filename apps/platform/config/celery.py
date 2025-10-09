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

# Periodic tasks
try:
    import os
    from datetime import timedelta

    recovery_interval_s = int(os.getenv("JOB_RECOVERY_BEAT_SECONDS", "60").strip())
    if recovery_interval_s < 10:
        recovery_interval_s = 10
    app.conf.beat_schedule = getattr(app.conf, "beat_schedule", {}) | {
        "recover-stale-jobs": {
            "task": "apps.platform.operations.tasks.recover_stale_jobs",
            "schedule": recovery_interval_s,
        }
    }
except Exception:
    # Do not fail worker initialization if schedule wiring encounters an error
    pass


@app.task(bind=True)
def ping(self: Any) -> str:  # pragma: no cover - trivial
    return "pong"
