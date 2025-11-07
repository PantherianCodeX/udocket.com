from __future__ import annotations

"""Import-forwarding shims for agent implementations.

Agents will ultimately live under the automation tree and call packages.ai.api
directly. While that refactor is underway, this module re-exports the existing
packages.core.agents surface so new imports resolve immediately.
"""

# pyright: strict
from packages.ai import DefaultAIClient, build_client
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

__all__ = [
    "AudioNormalizationResult",
    "TranscriptionAgent",
    "TranscriptionConfig",
    "TranscriptionResult",
    "AnalyzeAgent",
    "AnalyzeConfig",
    "AnalyzeResult",
    "ComposeAgent",
    "ComposeConfig",
    "ComposeResult",
    "GuardianAgent",
    "GuardianConfig",
    "GuardianVerdict",
    "GuardianRejection",
    "AnalyzeGraph",
    "AnalyzeNodeImpl",
    "build_analyze_graph",
    "ensure_wav",
    "normalize_audio",
    "DefaultAIClient",
    "build_client",
]
