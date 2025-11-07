from __future__ import annotations

from collections.abc import Mapping
from typing import Any

class Response:
    status_code: int

    def json(self) -> Any: ...

    def raise_for_status(self) -> None: ...


def post(
    url: str,
    *,
    headers: Mapping[str, str] | None = ...,
    data: str | bytes | None = ...,
    timeout: float | int | None = ...,
) -> Response: ...

__all__ = ["Response", "post"]
