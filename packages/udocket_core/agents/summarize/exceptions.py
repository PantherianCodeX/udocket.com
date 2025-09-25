from __future__ import annotations

from typing import Any


class AzureStageFailure(RuntimeError):
    """Raised when an Azure-backed stage fails but a fallback is available."""

    def __init__(self, stage: str, error: Exception, fallback: Any) -> None:
        message = f"Azure stage '{stage}' failed: {error}"
        super().__init__(message)
        self.stage = stage
        self.error = error
        self.fallback = fallback


class AzureUnavailableError(RuntimeError):
    """Raised when Azure is unavailable and offline fallback is not yet approved."""

    def __init__(self, stage: str, error: Exception) -> None:
        message = (
            "Azure OpenAI is unavailable during stage '{stage}'. Original error: {err}. "
            "Retry later or rerun summarize with allow_offline_fallback=True to continue with limited local processing."
        ).format(stage=stage, err=error)
        super().__init__(message)
        self.stage = stage
        self.error = error


__all__ = ["AzureStageFailure", "AzureUnavailableError"]
