# Copyright (c) 2025 uDocket Inc. All rights reserved.

from contextlib import AbstractContextManager
from types import TracebackType
from typing import overload, override

class MonkeyPatch:
    @overload
    def setattr(
        self,
        target: object,
        name: str,
        value: object,
        *,
        raising: bool = True,
    ) -> None: ...
    @overload
    def setattr(
        self,
        target: str,
        value: object,
        *,
        raising: bool = True,
    ) -> None: ...

class _RaisesContext(AbstractContextManager[None]):
    @override
    def __enter__(self) -> None: ...

    @override
    def __exit__(
        self,
        __exc_type: type[BaseException] | None,
        __exc_value: BaseException | None,
        __traceback: TracebackType | None,
        /,
    ) -> bool | None: ...

def raises(
    __expected_exception: type[BaseException] | tuple[type[BaseException], ...],
    /,
) -> _RaisesContext: ...
