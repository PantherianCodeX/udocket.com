from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MonkeyPatchProtocol(Protocol):
    def setattr(self, target: object, name: str, value: object, raising: bool = True) -> None:
        ...

    def setenv(self, name: str, value: str, *, prepend: bool = False) -> None:
        ...

    def delfunc(self, target: object, name: str, raising: bool = True) -> None:
        ...


MonkeyPatch = MonkeyPatchProtocol


class SettingsFixture(Protocol):
    def __getitem__(self, __name: str) -> Any:
        ...

    def __setitem__(self, __name: str, __value: Any) -> None:
        ...


class DatabaseFixture(Protocol):
    def __call__(self) -> None:
        ...


class ClientFixture(Protocol):
    def get(self, path: str, data: Mapping[str, Any] | None = None, **extra: Any) -> Any:
        ...

    def post(self, path: str, data: Mapping[str, Any] | None = None, **extra: Any) -> Any:
        ...
