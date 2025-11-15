"""Typed lane packages for the AI refactor automation pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Sequence

from packages.ai.api import ResidencyTag, RuntimeProfile
from packages.common.agents.stage_map import StageKey


class LaneID(StrEnum):
    ANALYZE = "ANALYZE"
    COMPOSE = "COMPOSE"


@dataclass(frozen=True)
class LanePackage:
    lane_id: LaneID
    stage_keys: tuple[StageKey, ...]
    ai_runtime_profile: RuntimeProfile
    qa_contracts: tuple[str, ...]
    cost_ceiling_tokens: int
    depends_on: tuple[LaneID, ...]
    residency_tag: ResidencyTag


def lane_key_sequence(keys: Sequence[StageKey]) -> tuple[StageKey, ...]:
    return tuple(keys)
