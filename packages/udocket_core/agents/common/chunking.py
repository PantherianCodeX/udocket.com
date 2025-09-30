from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

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
) -> Optional[tuple[str, str]]:
    cfg = config or ChunkSplitConfig()
    text = text.strip()
    if not text:
        return None

    lines = text.splitlines()
    if len(lines) >= cfg.min_lines:
        midpoint = len(lines) // 2
        left = "\n".join(lines[:midpoint]).strip()
        right = "\n".join(lines[midpoint:]).strip()
        if left and right:
            return left, right

    if len(text) >= cfg.min_chars * 2:
        midpoint = len(text) // 2
        left = text[:midpoint].rstrip()
        right = text[midpoint:].lstrip()
        if left and right:
            return left, right

    return None


def should_retry_for_length(message: str) -> bool:
    lowered = message.lower()
    return "empty completion" in lowered or "finish_reason='length'" in lowered or "finish_reason=length" in lowered or "length" in lowered


def should_retry_for_json(message: str) -> bool:
    lowered = message.lower()
    return "invalid json" in lowered or "jsondecodeerror" in lowered


__all__ = [
    "ChunkSplitConfig",
    "split_for_retry",
    "should_retry_for_length",
    "should_retry_for_json",
]
