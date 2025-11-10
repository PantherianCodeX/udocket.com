# pyright: strict
"""Typed stage catalogs describing LangGraph pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable, Mapping, Sequence

from packages.ai.types import AgentTask


class StageKey(StrEnum):
    """Named LangGraph stage identifiers."""

    # Analyze (canonical dotted identifiers)
    AN_INPUT_DISCOVERY = "analyze.input_discovery"
    AN_ATOMS_EXTRACT = "analyze.atoms_extract"
    AN_CONTEXT_BUILD = "analyze.context_builder"
    AN_OUTLINE_DRAFT = "analyze.extract_outline"
    AN_TIMELINE_BUILD = "analyze.build_timeline_seeds"
    AN_ENTITIES_EXTRACT = "analyze.build_entity_hints"
    AN_ISSUES_EXTRACT = "analyze.issues_extract"
    AN_GAPS_EXTRACT = "analyze.gaps_extract"
    AN_FLAGS_EXTRACT = "analyze.flags_extract"
    AN_SUMMARY_DRAFT = "analyze.draft_markdown"
    AN_STAFF_REPORT = "analyze.staff_report"
    AN_LANE_QA = "analyze.qa_and_finalize"
    AN_QA_JOIN = "analyze.qa_join"
    AN_FINALIZE_WRITE = "analyze.write_ops_and_artifacts"

    # Compose
    CO_CONTEXT_BUILD = "compose.context"
    CO_CLIENT_DRAFT = "compose.client.draft"
    CO_CLIENT_REVISE = "compose.client.revise"
    CO_CLIENT_QA = "compose.client.qa_reviewer"
    CO_CLIENT_EDITOR = "compose.client.editor"
    CO_LAWYER_DRAFT = "compose.lawyer.draft"
    CO_LAWYER_REVISE = "compose.lawyer.revise"
    CO_LAWYER_QA = "compose.lawyer.qa_reviewer"
    CO_LAWYER_EDITOR = "compose.lawyer.editor"
    CO_QA_JOIN = "compose.qa_join"
    CO_RELEASE_WRITE = "compose.release_gate"


@dataclass(frozen=True, slots=True)
class StageSpec:
    """Typed metadata for a LangGraph stage."""

    stage_key: StageKey
    agent_task: AgentTask | None
    depends_on: tuple[StageKey, ...] = ()
    llm_profile_id: str | None = None
    model_hint: str | None = None
    retry_budget: int = 1
    cost_ceiling: float | None = None
    enabled: bool = True


StageMap = Mapping[StageKey, StageSpec]


@dataclass(frozen=True, slots=True)
class StagePlan:
    """A topologically sorted, deterministic stage execution plan."""

    ordered: tuple[StageSpec, ...]

    def stage_keys(self) -> tuple[StageKey, ...]:
        return tuple(spec.stage_key for spec in self.ordered)


class StagePlanError(RuntimeError):
    """Raised when the stage map contains invalid or cyclic dependencies."""


def _topological_order(stage_map: StageMap) -> tuple[StageSpec, ...]:
    indegree: dict[StageKey, int] = {}
    dependents: dict[StageKey, list[StageKey]] = {}
    for key, spec in stage_map.items():
        indegree[key] = len(spec.depends_on)
        for dependency in spec.depends_on:
            if dependency not in stage_map:
                raise StagePlanError(f"Stage {key} depends on missing stage {dependency}")
            dependents.setdefault(dependency, []).append(key)

    queue = [key for key, degree in indegree.items() if degree == 0]
    ordered: list[StageSpec] = []

    while queue:
        queue.sort(key=lambda item: item.value)  # deterministic order
        current_key = queue.pop(0)
        ordered.append(stage_map[current_key])
        for child in dependents.get(current_key, []):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)

    if len(ordered) != len(stage_map):
        raise StagePlanError("Cycle detected in stage map")
    return tuple(ordered)


def build_stage_plan(stage_map: StageMap, *, include: Iterable[StageKey] | None = None) -> StagePlan:
    """Return a deterministic execution plan for the provided stage map."""

    if include is not None:
        subset = {key: stage_map[key] for key in include if stage_map[key].enabled}
    else:
        subset = {key: spec for key, spec in stage_map.items() if spec.enabled}
    ordered = _topological_order(subset)
    return StagePlan(ordered=ordered)


def _spec(
    stage_key: StageKey,
    agent_task: AgentTask | None,
    *,
    depends_on: Sequence[StageKey] = (),
    retry_budget: int = 1,
    enabled: bool = True,
) -> StageSpec:
    return StageSpec(
        stage_key=stage_key,
        agent_task=agent_task,
        depends_on=tuple(depends_on),
        retry_budget=retry_budget,
        enabled=enabled,
    )


ANALYZE_V1_STAGE_MAP: dict[StageKey, StageSpec] = {
    StageKey.AN_INPUT_DISCOVERY: _spec(StageKey.AN_INPUT_DISCOVERY, None),
    StageKey.AN_ATOMS_EXTRACT: _spec(
        StageKey.AN_ATOMS_EXTRACT,
        AgentTask.ATOMS,
        depends_on=[StageKey.AN_INPUT_DISCOVERY],
    ),
    StageKey.AN_CONTEXT_BUILD: _spec(
        StageKey.AN_CONTEXT_BUILD,
        None,
        depends_on=[StageKey.AN_ATOMS_EXTRACT],
    ),
    StageKey.AN_OUTLINE_DRAFT: _spec(
        StageKey.AN_OUTLINE_DRAFT,
        AgentTask.EXTRACT,
        depends_on=[StageKey.AN_CONTEXT_BUILD],
    ),
    StageKey.AN_TIMELINE_BUILD: _spec(
        StageKey.AN_TIMELINE_BUILD,
        AgentTask.EXTRACT,
        depends_on=[StageKey.AN_ATOMS_EXTRACT],
    ),
    StageKey.AN_ENTITIES_EXTRACT: _spec(
        StageKey.AN_ENTITIES_EXTRACT,
        AgentTask.EXTRACT,
        depends_on=[StageKey.AN_ATOMS_EXTRACT],
    ),
    StageKey.AN_ISSUES_EXTRACT: _spec(
        StageKey.AN_ISSUES_EXTRACT,
        AgentTask.EXTRACT,
        depends_on=[StageKey.AN_CONTEXT_BUILD],
        enabled=False,
    ),
    StageKey.AN_GAPS_EXTRACT: _spec(
        StageKey.AN_GAPS_EXTRACT,
        AgentTask.EXTRACT,
        depends_on=[StageKey.AN_CONTEXT_BUILD],
        enabled=False,
    ),
    StageKey.AN_FLAGS_EXTRACT: _spec(
        StageKey.AN_FLAGS_EXTRACT,
        AgentTask.EXTRACT,
        depends_on=[StageKey.AN_CONTEXT_BUILD],
        enabled=False,
    ),
    StageKey.AN_SUMMARY_DRAFT: _spec(
        StageKey.AN_SUMMARY_DRAFT,
        AgentTask.GENERATE,
        depends_on=[
            StageKey.AN_OUTLINE_DRAFT,
            StageKey.AN_TIMELINE_BUILD,
            StageKey.AN_ENTITIES_EXTRACT,
        ],
    ),
    StageKey.AN_STAFF_REPORT: _spec(
        StageKey.AN_STAFF_REPORT,
        AgentTask.GENERATE,
        depends_on=[StageKey.AN_SUMMARY_DRAFT],
        enabled=False,
    ),
    StageKey.AN_LANE_QA: _spec(
        StageKey.AN_LANE_QA,
        AgentTask.EVAL,
        depends_on=[StageKey.AN_SUMMARY_DRAFT],
    ),
    StageKey.AN_QA_JOIN: _spec(
        StageKey.AN_QA_JOIN,
        None,
        depends_on=[StageKey.AN_LANE_QA],
    ),
    StageKey.AN_FINALIZE_WRITE: _spec(
        StageKey.AN_FINALIZE_WRITE,
        None,
        depends_on=[StageKey.AN_QA_JOIN],
    ),
}


COMPOSE_V1_STAGE_MAP: dict[StageKey, StageSpec] = {
    StageKey.CO_CONTEXT_BUILD: _spec(StageKey.CO_CONTEXT_BUILD, None),
    StageKey.CO_CLIENT_DRAFT: _spec(
        StageKey.CO_CLIENT_DRAFT,
        AgentTask.GENERATE,
        depends_on=[StageKey.CO_CONTEXT_BUILD],
    ),
    StageKey.CO_CLIENT_QA: _spec(
        StageKey.CO_CLIENT_QA,
        AgentTask.EVAL,
        depends_on=[StageKey.CO_CLIENT_DRAFT],
    ),
    StageKey.CO_CLIENT_EDITOR: _spec(
        StageKey.CO_CLIENT_EDITOR,
        AgentTask.GENERATE,
        depends_on=[StageKey.CO_CLIENT_QA],
        enabled=False,
    ),
    StageKey.CO_CLIENT_REVISE: _spec(
        StageKey.CO_CLIENT_REVISE,
        AgentTask.GENERATE,
        depends_on=[StageKey.CO_CLIENT_QA],
        enabled=False,
    ),
    StageKey.CO_LAWYER_DRAFT: _spec(
        StageKey.CO_LAWYER_DRAFT,
        AgentTask.GENERATE,
        depends_on=[StageKey.CO_CONTEXT_BUILD],
    ),
    StageKey.CO_LAWYER_QA: _spec(
        StageKey.CO_LAWYER_QA,
        AgentTask.EVAL,
        depends_on=[StageKey.CO_LAWYER_DRAFT],
    ),
    StageKey.CO_LAWYER_EDITOR: _spec(
        StageKey.CO_LAWYER_EDITOR,
        AgentTask.GENERATE,
        depends_on=[StageKey.CO_LAWYER_QA],
        enabled=False,
    ),
    StageKey.CO_LAWYER_REVISE: _spec(
        StageKey.CO_LAWYER_REVISE,
        AgentTask.GENERATE,
        depends_on=[StageKey.CO_LAWYER_QA],
        enabled=False,
    ),
    StageKey.CO_QA_JOIN: _spec(
        StageKey.CO_QA_JOIN,
        None,
        depends_on=[StageKey.CO_CLIENT_QA, StageKey.CO_LAWYER_QA],
    ),
    StageKey.CO_RELEASE_WRITE: _spec(
        StageKey.CO_RELEASE_WRITE,
        None,
        depends_on=[StageKey.CO_QA_JOIN],
    ),
}

ANALYZE_V1_STAGE_PLAN = build_stage_plan(ANALYZE_V1_STAGE_MAP)
COMPOSE_V1_STAGE_PLAN = build_stage_plan(COMPOSE_V1_STAGE_MAP)


def get_stage_spec(stage_map: StageMap, stage_key: StageKey) -> StageSpec:
    """Return the StageSpec for the given key."""

    try:
        return stage_map[stage_key]
    except KeyError as exc:  # pragma: no cover - developer error
        raise KeyError(f"Stage {stage_key} missing from stage map") from exc


__all__ = [
    "StageKey",
    "StagePlan",
    "StageMap",
    "StageSpec",
    "StagePlanError",
    "ANALYZE_V1_STAGE_MAP",
    "ANALYZE_V1_STAGE_PLAN",
    "COMPOSE_V1_STAGE_MAP",
    "COMPOSE_V1_STAGE_PLAN",
    "build_stage_plan",
    "get_stage_spec",
]
