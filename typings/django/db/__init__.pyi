from __future__ import annotations

from typing import Any, Protocol
from types import TracebackType

from . import models, transaction


class Cursor(Protocol):
    def __enter__(self) -> Cursor: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None: ...

    def execute(self, sql: str, params: Any | None = ...) -> None: ...

    def fetchone(self) -> Any | None: ...


class Connection(Protocol):
    vendor: str

    def cursor(self) -> Cursor: ...


connection: Connection

__all__ = ["models", "transaction", "connection"]
