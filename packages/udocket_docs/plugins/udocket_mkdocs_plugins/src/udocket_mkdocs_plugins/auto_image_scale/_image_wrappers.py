from __future__ import annotations

# pyright: strict

import importlib
from types import TracebackType
from typing import Protocol, Type, runtime_checkable


@runtime_checkable
class ImageContext(Protocol):
    width: int
    height: int

    def load(self) -> None: ...

    def __enter__(self) -> ImageContext: ...

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...


def open_image(path: str) -> ImageContext:
    pil_image = importlib.import_module("PIL.Image")
    open_func = getattr(pil_image, "open", None)
    if not callable(open_func):  # pragma: no cover - defensive
        raise AttributeError("PIL.Image.open not available")
    image_obj = open_func(path)
    if not isinstance(image_obj, ImageContext):  # pragma: no cover - defensive
        raise TypeError("PIL.Image.open returned unexpected type")
    return image_obj
