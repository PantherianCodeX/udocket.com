# pyright: strict

from __future__ import annotations

from typing import Any, Mapping, Protocol, cast

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


class ChannelLayerProtocol(Protocol):
    async def group_send(self, group: str, message: Mapping[str, Any]) -> None: ...


def _send_group_message(group_name: str, message: Mapping[str, Any]) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    channel_layer = cast(ChannelLayerProtocol, layer)
    async_to_sync(channel_layer.group_send)(group_name, dict(message))


def send_job_update(job_id: str, **payload: Any) -> None:
    message: dict[str, Any] = {
        "type": "job.update",
        "job_id": job_id,
        **payload,
    }
    _send_group_message(f"jobs_{job_id}", message)


def send_case_update(case_id: str, **payload: Any) -> None:
    message: dict[str, Any] = {
        "type": "case.update",
        "case_id": case_id,
        **payload,
    }
    _send_group_message(f"cases_{case_id}", message)


__all__ = ["send_job_update", "send_case_update"]
