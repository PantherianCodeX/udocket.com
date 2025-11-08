from __future__ import annotations

from typing import Any, Mapping


class AsyncJsonWebsocketConsumer:
    scope: Mapping[str, Any]
    channel_layer: Any
    channel_name: str

    async def accept(self) -> None: ...

    async def close(self, code: int | None = ...) -> None: ...

    async def send_json(self, content: Mapping[str, Any]) -> None: ...
