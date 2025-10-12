from __future__ import annotations

# pyright: strict

import logging
from typing import Callable

from .llm.runtime import SupportsHealthCheck


def ensure_llm_client_health(
    client: object,
    *,
    stage: str,
    provider: str,
    model: str,
    logger: logging.Logger,
    raise_error: Callable[[str], Exception],
) -> None:
    """Run provider health checks when supported.

    Args:
        client: Chat client instance which may implement ``SupportsHealthCheck``.
        stage: Logical stage identifier (e.g., ``"analyze.extract_outline"``).
        provider: Provider name for logging context.
        model: Model identifier for logging context.
        logger: Logger used to record failures.
        raise_error: Factory that receives a reason string and returns an exception.
    """

    if not isinstance(client, SupportsHealthCheck):
        return
    try:
        client.health_check()
    except Exception as exc:
        reason = f"Health check failed: {exc}"
        logger.error(
            "llm.health.failed",
            extra={
                "stage": stage,
                "provider": provider,
                "model": model,
                "error": str(exc),
            },
        )
        raise raise_error(reason) from exc


__all__ = ["ensure_llm_client_health"]
