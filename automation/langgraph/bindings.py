# pyright: strict
"""Shared helpers for binding StageKeys to LangGraph node implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from packages.common.agents import StageKey, StagePlan


@dataclass(slots=True, frozen=True)
class StageBinding:
    """Deterministic binding between a StageKey and a node method."""

    stage_key: StageKey
    method_name: str


def resolve_stage_bindings(
    stage_plan: StagePlan,
    binding_map: Mapping[StageKey, str],
) -> list[StageBinding]:
    """Return ordered StageBindings for the provided StagePlan."""

    bindings: list[StageBinding] = []
    for spec in stage_plan.ordered:
        method_name = binding_map.get(spec.stage_key)
        if method_name is None:
            msg = f"No LangGraph node implementation bound for {spec.stage_key}"
            raise KeyError(msg)
        bindings.append(StageBinding(stage_key=spec.stage_key, method_name=method_name))
    return bindings


__all__ = ["StageBinding", "resolve_stage_bindings"]
