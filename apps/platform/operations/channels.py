# pyright: strict

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, cast

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from packages.common.json_utils import JSONValue
from packages.common.operations import CaseUpdatePayload, JobUpdatePayload


class ChannelLayerProtocol(Protocol):
    async def group_send(self, group: str, message: Mapping[str, JSONValue]) -> None: ...


def _send_group_message(group_name: str, message: Mapping[str, JSONValue]) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    channel_layer = cast(ChannelLayerProtocol, layer)
    async_to_sync(channel_layer.group_send)(group_name, dict(message))


def send_job_update(job_id: str, **payload: JSONValue) -> None:
    wrapper = JobUpdatePayload.create(job_id, payload)
    _send_group_message(wrapper.group, wrapper.message())


def send_case_update(case_id: str, **payload: JSONValue) -> None:
    wrapper = CaseUpdatePayload.create(case_id, payload)
    _send_group_message(wrapper.group, wrapper.message())


__all__ = ["send_job_update", "send_case_update"]
