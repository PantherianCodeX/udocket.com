from __future__ import annotations

from typing import Any, cast

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def send_job_update(job_id: str, **payload: object) -> None:
    layer = cast(Any, get_channel_layer())
    if layer is None:
        return
    message: dict[str, object] = {"type": "job.update", "job_id": job_id, **payload}
    async_to_sync(layer.group_send)(f"jobs_{job_id}", message)


def send_case_update(case_id: str, **payload: object) -> None:
    layer = cast(Any, get_channel_layer())
    if layer is None:
        return
    message: dict[str, object] = {"type": "case.update", "case_id": case_id, **payload}
    async_to_sync(layer.group_send)(f"cases_{case_id}", message)
