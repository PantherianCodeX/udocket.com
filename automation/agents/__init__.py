# pyright: strict
"""Import-forwarding shims for agent implementations.

Agents will ultimately live under the automation tree and call packages.ai.api
directly. While that refactor is underway, this module re-exports the existing
packages.core.agents surface so new imports resolve immediately.
"""

from __future__ import annotations

from packages.core.agents import (
    AnalyzeAgent as _BaseAnalyzeAgent,
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
from packages.core.agents.analyze_lib import GraphBuilder

from automation.langgraph import build_analyze_graph_v1
from .ai_factory import get_ai_client


class AnalyzeAgent(_BaseAnalyzeAgent):
    """Automation-facing AnalyzeAgent that defaults to the StagePlan builder."""

    def __init__(
        self,
        config: AnalyzeConfig | None = None,
        *,
        ai_client: "AIClient | None" = None,
        langgraph_builder: GraphBuilder | None = None,
    ) -> None:
        super().__init__(
            config=config,
            ai_client=ai_client,
            langgraph_builder=langgraph_builder or build_analyze_graph_v1,
        )

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
    "build_analyze_graph_v1",
    "ensure_wav",
    "get_ai_client",
    "normalize_audio",
]
