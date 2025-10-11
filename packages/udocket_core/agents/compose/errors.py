from __future__ import annotations

# pyright: strict

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class ComposeStageContext:
    stage: str
    lane: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    attempt: Optional[int] = None


class ComposeStageError(RuntimeError):
    """Error raised when a compose stage fails.

    Captures execution context (lane, provider, model, attempt) to make upstream
    exception handling and logging more actionable.
    """

    def __init__(
        self,
        stage: str,
        message: str,
        *,
        lane: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        attempt: Optional[int] = None,
    ) -> None:
        context = ComposeStageContext(
            stage=stage,
            lane=lane,
            provider=provider,
            model=model,
            attempt=attempt,
        )
        suffix_parts: list[str] = []
        if context.lane:
            suffix_parts.append(f"lane={context.lane}")
        if context.provider:
            suffix_parts.append(f"provider={context.provider}")
        if context.model:
            suffix_parts.append(f"model={context.model}")
        if context.attempt is not None:
            suffix_parts.append(f"attempt={context.attempt}")
        suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
        super().__init__(f"{context.stage}: {message}{suffix}")
        self.stage = context.stage
        self.lane = context.lane
        self.provider = context.provider
        self.model = context.model
        self.attempt = context.attempt


__all__ = ["ComposeStageError", "ComposeStageContext"]
