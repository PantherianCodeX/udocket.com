from __future__ import annotations

from typing import Any, Mapping, Protocol


class ChannelLayerProtocol(Protocol):
    async def group_add(self, group: str, channel: str) -> None: ...

    async def group_discard(self, group: str, channel: str) -> None: ...

    async def group_send(self, group: str, message: Mapping[str, Any]) -> None: ...


def get_channel_layer() -> ChannelLayerProtocol | None: ...


__all__ = ["ChannelLayerProtocol", "get_channel_layer"]
