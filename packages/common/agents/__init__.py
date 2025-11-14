# pyright: strict

"""Shared agent-facing dataclasses and protocols."""

from __future__ import annotations

from .base import AnalysisArtifact, AnalysisResult
from .results import RegionLiteral, TranscriptionResult
from .stage_map import (
    ANALYZE_V1_STAGE_MAP,
    ANALYZE_V1_STAGE_PLAN,
    COMPOSE_V1_STAGE_MAP,
    COMPOSE_V1_STAGE_PLAN,
    StageKey,
    StageMap,
    StagePlan,
    StagePlanError,
    StageSpec,
    build_stage_plan,
    get_stage_spec,
)
from .stage_overrides import (
    StageOverrideConfig,
    normalize_stage_override_mapping,
    parse_stage_overrides,
    stage_overrides_by_name,
    stage_overrides_to_json,
)

__all__ = [
    "TranscriptionResult",
    "RegionLiteral",
    "AnalysisArtifact",
    "AnalysisResult",
    "StageKey",
    "StageSpec",
    "StagePlan",
    "StagePlanError",
    "StageMap",
    "ANALYZE_V1_STAGE_MAP",
    "ANALYZE_V1_STAGE_PLAN",
    "COMPOSE_V1_STAGE_MAP",
    "COMPOSE_V1_STAGE_PLAN",
    "build_stage_plan",
    "get_stage_spec",
    "StageOverrideConfig",
    "normalize_stage_override_mapping",
    "parse_stage_overrides",
    "stage_overrides_by_name",
    "stage_overrides_to_json",
]
