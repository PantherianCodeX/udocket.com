"""Lane definitions and validation helpers for automation pipelines."""

from __future__ import annotations

from typing import Iterable, Mapping

from packages.common.agents.stage_map import StageKey

from automation.pipelines.models import LaneID, LanePackage, ResidencyTag, RuntimeProfile


def _lane_map() -> Mapping[LaneID, LanePackage]:
    return {
        LaneID.ANALYZE: LanePackage(
            lane_id=LaneID.ANALYZE,
            stage_keys=(
                StageKey.AN_INPUT_DISCOVERY,
                StageKey.AN_ATOMS_EXTRACT,
                StageKey.AN_CONTEXT_BUILD,
                StageKey.AN_OUTLINE_DRAFT,
                StageKey.AN_TIMELINE_BUILD,
                StageKey.AN_ENTITIES_EXTRACT,
                StageKey.AN_SUMMARY_DRAFT,
                StageKey.AN_LANE_QA,
                StageKey.AN_QA_JOIN,
                StageKey.AN_FINALIZE_WRITE,
            ),
            ai_runtime_profile=RuntimeProfile.ANALYZE,
            qa_contracts=("QA-AUTOMATION-ANALYZE",),
            cost_ceiling_tokens=1200,
            depends_on=(),
            residency_tag=ResidencyTag.US_EAST,
        ),
        LaneID.COMPOSE: LanePackage(
            lane_id=LaneID.COMPOSE,
            stage_keys=(
                StageKey.CO_CONTEXT_BUILD,
                StageKey.CO_CLIENT_DRAFT,
                StageKey.CO_CLIENT_QA,
                StageKey.CO_CLIENT_EDITOR,
                StageKey.CO_CLIENT_REVISE,
                StageKey.CO_LAWYER_DRAFT,
                StageKey.CO_LAWYER_QA,
                StageKey.CO_LAWYER_EDITOR,
                StageKey.CO_LAWYER_REVISE,
                StageKey.CO_QA_JOIN,
                StageKey.CO_RELEASE_WRITE,
            ),
            ai_runtime_profile=RuntimeProfile.COMPOSE,
            qa_contracts=("QA-AUTOMATION-COMPOSE",),
            cost_ceiling_tokens=1600,
            depends_on=(LaneID.ANALYZE,),
            residency_tag=ResidencyTag.EU_CENTRAL,
        ),
    }


def lane_packages() -> tuple[LanePackage, ...]:
    return tuple(_lane_map().values())


def lane_package_map() -> Mapping[LaneID, LanePackage]:
    return _lane_map()


def lane_dependencies() -> Mapping[LaneID, Iterable[LaneID]]:
    return {lane.lane_id: lane.depends_on for lane in lane_packages()}
