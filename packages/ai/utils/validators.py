# pyright: strict

"""Validation helpers for API payloads."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packages.ai.api import SummarizeRequest

_ERROR_TRANSCRIPT_EMPTY = "SummarizeRequest.transcript must not be empty"


def ensure_request_invariants(request: SummarizeRequest) -> None:
    """Example invariant: transcript must not be empty."""

    if not request.transcript.strip():
        raise ValueError(_ERROR_TRANSCRIPT_EMPTY)


__all__ = ["ensure_request_invariants"]
