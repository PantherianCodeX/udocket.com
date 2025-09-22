from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def send_job_update(job_id: str, **payload) -> None:
    layer = get_channel_layer()
    message = {"type": "job.update", "job_id": str(job_id), **payload}
    async_to_sync(layer.group_send)(f"jobs_{job_id}", message)


def send_case_update(case_id: str, **payload) -> None:
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(f"cases_{case_id}", {"type": "case.update", **payload})
