# pyright: strict
"""Import-forwarding shims for agent implementations.

Agents will ultimately live under the automation tree and call packages.ai.api
directly. While that refactor is underway, this module re-exports the existing
packages.core.agents surface so new imports resolve immediately.
"""

from __future__ import annotations

from packages.core.agents import (
    AnalyzeAgent,
    AnalyzeConfig,
    AnalyzeGraph,
    AnalyzeNodeImpl,
    AnalyzeResult,
    AudioNormalizationResult,
    ComposeAgent,
    ComposeConfig,
    ComposeResult,
    GuardianAgent,
    GuardianConfig,
    GuardianRejection,
    GuardianVerdict,
    TranscriptionAgent,
    TranscriptionConfig,
    TranscriptionResult,
    build_analyze_graph,
    ensure_wav,
    normalize_audio,
)

from .ai_factory import get_ai_client

__all__ = [
    "AnalyzeAgent",
    "AnalyzeConfig",
    "AnalyzeGraph",
    "AnalyzeNodeImpl",
    "AnalyzeResult",
    "AudioNormalizationResult",
    "ComposeAgent",
    "ComposeConfig",
    "ComposeResult",
    "GuardianAgent",
    "GuardianConfig",
    "GuardianRejection",
    "GuardianVerdict",
    "TranscriptionAgent",
    "TranscriptionConfig",
    "TranscriptionResult",
    "build_analyze_graph",
    "ensure_wav",
    "get_ai_client",
    "normalize_audio",
]
