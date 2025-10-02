"""Stage profile metadata for the Compose pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ComposeStageProfile:
    stage_key: str
    label: str
    description: str
    min_context_tokens: int
    recommended_context_tokens: int
    target_chunk_tokens: int
    output_reserve_tokens: int
    resource_notes: str | None = None


COMPOSE_STAGE_PROFILES: Dict[str, ComposeStageProfile] = {
    "compose.context_builder": ComposeStageProfile(
        stage_key="compose.context_builder",
        label="Context Builder",
        description="Condense intake metadata and the approved summary into a case brief for downstream stages.",
        min_context_tokens=16000,
        recommended_context_tokens=32000,
        target_chunk_tokens=8000,
        output_reserve_tokens=2000,
        resource_notes="Supply intake fields, staff report highlights, and summary excerpts.",
    ),
    "compose.timeline_builder": ComposeStageProfile(
        stage_key="compose.timeline_builder",
        label="Timeline Builder",
        description="Generate normalized timeline events with timestamp references for compose deliverables.",
        min_context_tokens=32000,
        recommended_context_tokens=64000,
        target_chunk_tokens=12000,
        output_reserve_tokens=4000,
        resource_notes="Chunk transcript segments with timestamps; include approved summary callouts when available.",
    ),
    "compose.graph_builder": ComposeStageProfile(
        stage_key="compose.graph_builder",
        label="Graph Builder",
        description="Extract entities and relationships with evidence links for compose outputs.",
        min_context_tokens=32000,
        recommended_context_tokens=64000,
        target_chunk_tokens=12000,
        output_reserve_tokens=4000,
        resource_notes="Provide speaker metadata and prior entity hints to improve grounding.",
    ),
    "compose.timeline_summary": ComposeStageProfile(
        stage_key="compose.timeline_summary",
        label="Timeline Narrative",
        description="Draft a succinct narrative of the timeline events for reuse in briefs and QA stages.",
        min_context_tokens=20000,
        recommended_context_tokens=40000,
        target_chunk_tokens=8000,
        output_reserve_tokens=4000,
        resource_notes="Feed normalized timeline events and summarize key milestones with timestamps.",
    ),
    "compose.entity_brief": ComposeStageProfile(
        stage_key="compose.entity_brief",
        label="Entity Briefing",
        description="Summarize principal entities, roles, and relationships for quick reference sections.",
        min_context_tokens=20000,
        recommended_context_tokens=40000,
        target_chunk_tokens=8000,
        output_reserve_tokens=3000,
        resource_notes="Combine entity hints, graph payload, and intake metadata to anchor roles.",
    ),
    "compose.graph_visual": ComposeStageProfile(
        stage_key="compose.graph_visual",
        label="Graph Visual Planner",
        description="Produce embeddable HTML/visual settings for the relationship graph with accessibility copy.",
        min_context_tokens=16000,
        recommended_context_tokens=32000,
        target_chunk_tokens=6000,
        output_reserve_tokens=2000,
        resource_notes="Return HTML embed snippets, size recommendations, and alt text.",
    ),
    "compose.client_brief": ComposeStageProfile(
        stage_key="compose.client_brief",
        label="Client Brief Drafter",
        description="Draft a client-facing deliverable at a grade-six reading level with clear next steps.",
        min_context_tokens=40000,
        recommended_context_tokens=80000,
        target_chunk_tokens=16000,
        output_reserve_tokens=6000,
        resource_notes="Ensure tone guidance and timeline highlights are present in the prompt context.",
    ),
    "compose.lawyer_brief": ComposeStageProfile(
        stage_key="compose.lawyer_brief",
        label="Lawyer Brief Drafter",
        description="Draft a professional deliverable for counsel organized by legal issues and evidence.",
        min_context_tokens=50000,
        recommended_context_tokens=100000,
        target_chunk_tokens=20000,
        output_reserve_tokens=8000,
        resource_notes="Include citations to transcript timestamps and timeline event identifiers.",
    ),
    "compose.qa_review": ComposeStageProfile(
        stage_key="compose.qa_review",
        label="QA Reviewer",
        description="Perform compliance checks on compose outputs and highlight remediation guidance.",
        min_context_tokens=16000,
        recommended_context_tokens=32000,
        target_chunk_tokens=6000,
        output_reserve_tokens=2000,
        resource_notes="Pass in rendered Markdown, timeline, and graph metadata for verification.",
    ),
}


__all__ = [
    "COMPOSE_STAGE_PROFILES",
    "ComposeStageProfile",
]
