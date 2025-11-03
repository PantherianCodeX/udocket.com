from __future__ import annotations

from typing import Iterable, Protocol, Sequence

class _SupportsWritePdf(Protocol):
    def write_pdf(
        self,
        target: str,
        *,
        stylesheets: Sequence[CSS] | None = ...,
        presentational_hints: bool = ...,
    ) -> None: ...

class CSS:
    def __init__(self, filename: str | None = ..., string: str | None = ...) -> None: ...

class HTML:
    def __init__(self, filename: str | None = ..., base_url: str | None = ..., string: str | None = ...) -> None: ...

    def write_pdf(
        self,
        target: str,
        *,
        stylesheets: Sequence[CSS] | None = ...,
        presentational_hints: bool = ...,
    ) -> None: ...

