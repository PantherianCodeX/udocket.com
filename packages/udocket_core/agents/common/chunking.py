from __future__ import annotations

# pyright: strict

from dataclasses import dataclass

DEFAULT_MIN_LINES = 8
DEFAULT_MIN_CHARS = 2000


@dataclass(frozen=True)
class ChunkSplitConfig:
    min_lines: int = DEFAULT_MIN_LINES
    min_chars: int = DEFAULT_MIN_CHARS


def split_for_retry(
    text: str,
    *,
    config: ChunkSplitConfig | None = None,
) -> tuple[str, str] | None:
    cfg = config or ChunkSplitConfig()
    trimmed = text.strip()
    if not trimmed:
        return None

    lines = trimmed.splitlines()
    if len(lines) >= cfg.min_lines:
        midpoint = len(lines) // 2
        left = "\n".join(lines[:midpoint]).strip()
        right = "\n".join(lines[midpoint:]).strip()
        if left and right:
            return left, right

    if len(trimmed) >= cfg.min_chars * 2:
        midpoint = len(trimmed) // 2
        left = trimmed[:midpoint].rstrip()
        right = trimmed[midpoint:].lstrip()
        if left and right:
            return left, right

    return None


def should_retry_for_length(message: str) -> bool:
    lowered = message.lower()
    return any(
        token in lowered
        for token in (
            "empty completion",
            "finish_reason='length'",
            "finish_reason=length",
            "length",
        )
    )


def should_retry_for_json(message: str) -> bool:
    lowered = message.lower()
    return any(
        token in lowered for token in ("invalid json", "jsondecodeerror", "json decode error")
    )


__all__ = [
    "ChunkSplitConfig",
    "split_for_retry",
    "should_retry_for_length",
    "should_retry_for_json",
]
