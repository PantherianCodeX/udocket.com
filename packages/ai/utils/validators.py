from __future__ import annotations

# pyright: strict

"""Validation helpers for API payloads."""

from ..api import SummarizeRequest


def ensure_request_invariants(request: SummarizeRequest) -> None:
    """Example invariant: transcript must not be empty."""

    if not request.transcript.strip():
        raise ValueError("SummarizeRequest.transcript must not be empty")


__all__ = ["ensure_request_invariants"]
