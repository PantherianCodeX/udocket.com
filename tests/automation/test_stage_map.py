from __future__ import annotations

import pytest

from packages.common.agents import (
    ANALYZE_V1_STAGE_MAP,
    ANALYZE_V1_STAGE_PLAN,
    COMPOSE_V1_STAGE_MAP,
    StageSpec,
    StageKey,
    StagePlanError,
    build_stage_plan,
    get_stage_spec,
)
from packages.ai.types import AgentTask


def test_analyze_summary_depends_on_all_lanes() -> None:
    summary_spec = ANALYZE_V1_STAGE_MAP[StageKey.AN_SUMMARY_DRAFT]
    assert summary_spec.agent_task is AgentTask.GENERATE
    assert StageKey.AN_OUTLINE_DRAFT in summary_spec.depends_on
    assert StageKey.AN_TIMELINE_BUILD in summary_spec.depends_on
    assert StageKey.AN_ENTITIES_EXTRACT in summary_spec.depends_on


def test_compose_editor_stage_disabled_by_default() -> None:
    editor_spec = COMPOSE_V1_STAGE_MAP[StageKey.CO_CLIENT_EDITOR]
    assert editor_spec.agent_task is AgentTask.GENERATE
    assert StageKey.CO_CLIENT_QA in editor_spec.depends_on
    assert not editor_spec.enabled


def test_get_stage_spec_raises_for_missing_key() -> None:
    with pytest.raises(KeyError):
        get_stage_spec(ANALYZE_V1_STAGE_MAP, StageKey.CO_CLIENT_DRAFT)


def test_stage_plan_orders_dependencies() -> None:
    ordered = ANALYZE_V1_STAGE_PLAN.stage_keys()
    assert ordered.index(StageKey.AN_ATOMS_EXTRACT) > ordered.index(StageKey.AN_INPUT_DISCOVERY)
    assert ordered.index(StageKey.AN_FINALIZE_WRITE) > ordered.index(StageKey.AN_LANE_QA)


def test_build_stage_plan_detects_cycle() -> None:
    broken = dict(ANALYZE_V1_STAGE_MAP)
    broken[StageKey.AN_INPUT_DISCOVERY] = StageSpec(  # type: ignore[misc]
        stage_key=StageKey.AN_INPUT_DISCOVERY,
        agent_task=None,
        depends_on=(StageKey.AN_FINALIZE_WRITE,),
    )
    with pytest.raises(StagePlanError):
        build_stage_plan(broken)
