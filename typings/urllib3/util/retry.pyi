from __future__ import annotations

from typing import Iterable

class Retry:
    def __init__(
        self,
        total: int | None = ...,
        connect: int | None = ...,
        read: int | None = ...,
        status: int | None = ...,
        backoff_factor: float = ...,
        status_forcelist: Iterable[int] | None = ...,
        allowed_methods: Iterable[str] | None = ...,
        respect_retry_after_header: bool = ...,
        raise_on_status: bool | None = ...,
    ) -> None: ...
