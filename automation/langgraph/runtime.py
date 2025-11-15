"""Runtime helpers that materialize langgraph lane packages."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence
from uuid import UUID, uuid4

from automation.pipelines.stage_map import lane_package_map, lane_packages
from automation.pipelines.models import LaneID, LanePackage
from packages.ai.telemetry.config import append_residency_entry
from packages.common.agents.stage_map import StageKey
from packages.common.types import FeatureID, ResidencyLedgerEntry
from packages.ai.api import ResidencyTag, RuntimeProfile


def load_lane_packages() -> tuple[LanePackage, ...]:
    return lane_packages()


def dependencies() -> dict[LaneID, tuple[LaneID, ...]]:
    return {lane.lane_id: lane.depends_on for lane in load_lane_packages()}


def execution_order() -> tuple[LanePackage, ...]:
    resolved: list[LanePackage] = []
    visited: set[LaneID] = set()
    stack: set[LaneID] = set()

    def visit(lane: LanePackage) -> None:
        if lane.lane_id in visited:
            return
        if lane.lane_id in stack:
            raise RuntimeError(f"cycle detected: {lane.lane_id}")
        stack.add(lane.lane_id)
        for dep in lane.depends_on:
            visit(lane_package_map()[dep])
        stack.remove(lane.lane_id)
        visited.add(lane.lane_id)
        resolved.append(lane)

    for lane in load_lane_packages():
        visit(lane)
    return tuple(resolved)


def lane_profiles() -> dict[RuntimeProfile, LanePackage]:
    return {lane.ai_runtime_profile: lane for lane in load_lane_packages()}


def residency_tags() -> dict[ResidencyTag, LanePackage]:
    return {lane.residency_tag: lane for lane in load_lane_packages()}


def publish_residency_entry(
    *,
    run_id: UUID,
    stage_key: StageKey,
    residency_tag: ResidencyTag,
    telemetry_bundle_path: Path,
    langsmith_eval_ids: Sequence[UUID],
    langfuse_session_id: UUID | None = None,
    disconnect_event: bool = False,
) -> ResidencyLedgerEntry:
    entry = ResidencyLedgerEntry(
        ledger_id=uuid4(),
        feature_id=FeatureID.REFRACTOR_002,
        run_id=run_id,
        stage_key=stage_key,
        residency_tag=residency_tag,
        telemetry_bundle_path=telemetry_bundle_path,
        langsmith_eval_ids=tuple(langsmith_eval_ids),
        langfuse_session_id=langfuse_session_id,
        disconnect_event=disconnect_event,
        timestamp=datetime.now(timezone.utc),
    )
    append_residency_entry(entry)
    return entry
