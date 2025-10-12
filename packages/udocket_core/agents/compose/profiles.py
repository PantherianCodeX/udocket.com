# pyright: strict

from __future__ import annotations

from dataclasses import dataclass


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


COMPOSE_STAGE_PROFILES: dict[str, ComposeStageProfile] = {
    "compose.context": ComposeStageProfile(
        stage_key="compose.context",
        label="Context Assembler",
        description="Condense intake metadata, staff findings, and approved summary outputs into ComposeContext.",
        min_context_tokens=16000,
        recommended_context_tokens=32000,
        target_chunk_tokens=8000,
        output_reserve_tokens=2000,
        resource_notes="Include intake answers, staff report highlights, and timeline/entity payloads when present.",
    ),
    "compose.client.draft": ComposeStageProfile(
        stage_key="compose.client.draft",
        label="Client Draft Composer",
        description="Draft the client-facing Markdown deliverable with mandated headings and empathetic tone.",
        min_context_tokens=40000,
        recommended_context_tokens=80000,
        target_chunk_tokens=16000,
        output_reserve_tokens=6000,
        resource_notes="Supply ComposeContext JSON and tone guardrails; cite transcript timestamps when available.",
    ),
    "compose.client.revise": ComposeStageProfile(
        stage_key="compose.client.revise",
        label="Client Revision Composer",
        description="Apply revision briefs to the client deliverable after guard or QA feedback.",
        min_context_tokens=40000,
        recommended_context_tokens=80000,
        target_chunk_tokens=16000,
        output_reserve_tokens=6000,
        resource_notes="Provide the previous draft, revision brief, and outstanding guard errors in context.",
    ),
    "compose.client.structure": ComposeStageProfile(
        stage_key="compose.client.structure",
        label="Client Structure Guard",
        description="Deterministically verify client headings, ordering, and section length requirements.",
        min_context_tokens=4000,
        recommended_context_tokens=8000,
        target_chunk_tokens=2000,
        output_reserve_tokens=500,
        resource_notes="Pass rendered Markdown only; no LLM usage for this guard.",
    ),
    "compose.client.compliance": ComposeStageProfile(
        stage_key="compose.client.compliance",
        label="Client Compliance Guard",
        description="Detect advice, predictions, or disallowed tone within the client deliverable.",
        min_context_tokens=4000,
        recommended_context_tokens=8000,
        target_chunk_tokens=2000,
        output_reserve_tokens=500,
        resource_notes="Pure Python guard – ensure most recent draft text is supplied.",
    ),
    "compose.client.factuality": ComposeStageProfile(
        stage_key="compose.client.factuality",
        label="Client Factuality Guard",
        description="Validate timestamp coverage and claim support for the client deliverable.",
        min_context_tokens=6000,
        recommended_context_tokens=12000,
        target_chunk_tokens=4000,
        output_reserve_tokens=1000,
        resource_notes="Requires ComposeContext claimable atoms and timeline seeds for cross-checks.",
    ),
    "compose.client.qa_reviewer": ComposeStageProfile(
        stage_key="compose.client.qa_reviewer",
        label="Client QA Reviewer",
        description="LLM QA pass covering structure, compliance, and factuality for the client lane.",
        min_context_tokens=16000,
        recommended_context_tokens=32000,
        target_chunk_tokens=6000,
        output_reserve_tokens=2000,
        resource_notes="Provide latest draft, ComposeContext, and guard findings when QA is enabled.",
    ),
    "compose.client.qa_revision": ComposeStageProfile(
        stage_key="compose.client.qa_revision",
        label="Client QA Revision Router",
        description="Prepares revision briefs and resets lane state according to QA directives.",
        min_context_tokens=2000,
        recommended_context_tokens=4000,
        target_chunk_tokens=1000,
        output_reserve_tokens=250,
        resource_notes="Non-LLM stage – passes revision briefs back into the drafting loop.",
    ),
    "compose.client.editor": ComposeStageProfile(
        stage_key="compose.client.editor",
        label="Client Lane Editor",
        description="Perform constrained, non-factual edits requested by QA for the client deliverable.",
        min_context_tokens=8000,
        recommended_context_tokens=16000,
        target_chunk_tokens=4000,
        output_reserve_tokens=1500,
        resource_notes="Context should include revision brief, allowed edit types, and latest draft.",
    ),
    "compose.lawyer.draft": ComposeStageProfile(
        stage_key="compose.lawyer.draft",
        label="Lawyer Draft Composer",
        description="Draft the lawyer-facing Markdown brief with evidentiary framing and required headings.",
        min_context_tokens=50000,
        recommended_context_tokens=100000,
        target_chunk_tokens=20000,
        output_reserve_tokens=8000,
        resource_notes="Supply ComposeContext, transcript cites, and outstanding legal issues for reference.",
    ),
    "compose.lawyer.revise": ComposeStageProfile(
        stage_key="compose.lawyer.revise",
        label="Lawyer Revision Composer",
        description="Apply revision briefs to the lawyer deliverable after guard or QA feedback.",
        min_context_tokens=50000,
        recommended_context_tokens=100000,
        target_chunk_tokens=20000,
        output_reserve_tokens=8000,
        resource_notes="Provide the latest draft, revision brief, and guard deltas for the lane.",
    ),
    "compose.lawyer.structure": ComposeStageProfile(
        stage_key="compose.lawyer.structure",
        label="Lawyer Structure Guard",
        description="Deterministically verify lawyer headings, ordering, and section length requirements.",
        min_context_tokens=4000,
        recommended_context_tokens=8000,
        target_chunk_tokens=2000,
        output_reserve_tokens=500,
        resource_notes="Pure Python guard – ensure full draft text is evaluated.",
    ),
    "compose.lawyer.compliance": ComposeStageProfile(
        stage_key="compose.lawyer.compliance",
        label="Lawyer Compliance Guard",
        description="Detect disallowed advice, advocacy, or speculative language in the lawyer deliverable.",
        min_context_tokens=4000,
        recommended_context_tokens=8000,
        target_chunk_tokens=2000,
        output_reserve_tokens=500,
        resource_notes="Non-LLM stage running compliance heuristics over the latest draft.",
    ),
    "compose.lawyer.factuality": ComposeStageProfile(
        stage_key="compose.lawyer.factuality",
        label="Lawyer Factuality Guard",
        description="Validate timestamp coverage and claim support for the lawyer deliverable.",
        min_context_tokens=6000,
        recommended_context_tokens=12000,
        target_chunk_tokens=4000,
        output_reserve_tokens=1000,
        resource_notes="Requires ComposeContext claimable atoms, timeline seeds, and entity hints.",
    ),
    "compose.lawyer.qa_reviewer": ComposeStageProfile(
        stage_key="compose.lawyer.qa_reviewer",
        label="Lawyer QA Reviewer",
        description="LLM QA pass covering structure, compliance, and factuality for the lawyer lane.",
        min_context_tokens=16000,
        recommended_context_tokens=32000,
        target_chunk_tokens=6000,
        output_reserve_tokens=2000,
        resource_notes="Provide latest lawyer draft, ComposeContext, and guard summaries when QA is enabled.",
    ),
    "compose.lawyer.qa_revision": ComposeStageProfile(
        stage_key="compose.lawyer.qa_revision",
        label="Lawyer QA Revision Router",
        description="Prepares revision briefs and resets the lawyer lane according to QA directives.",
        min_context_tokens=2000,
        recommended_context_tokens=4000,
        target_chunk_tokens=1000,
        output_reserve_tokens=250,
        resource_notes="Non-LLM stage that forwards revision briefs back into the drafting loop.",
    ),
    "compose.lawyer.editor": ComposeStageProfile(
        stage_key="compose.lawyer.editor",
        label="Lawyer Lane Editor",
        description="Perform constrained, non-factual edits requested by QA for the lawyer deliverable.",
        min_context_tokens=8000,
        recommended_context_tokens=16000,
        target_chunk_tokens=4000,
        output_reserve_tokens=1500,
        resource_notes="Context should include revision brief, allowed edit types, and latest draft.",
    ),
    "compose.qa_join": ComposeStageProfile(
        stage_key="compose.qa_join",
        label="QA Joiner",
        description="Combine lane QA payloads into a unified staff report and directive map.",
        min_context_tokens=4000,
        recommended_context_tokens=8000,
        target_chunk_tokens=2000,
        output_reserve_tokens=500,
        resource_notes="Aggregates lane QA results; no LLM invocation.",
    ),
    "compose.release_gate": ComposeStageProfile(
        stage_key="compose.release_gate",
        label="Release Gate",
        description="Final guard ensuring both lanes have passing outcomes and QA approvals before artifact write-out.",
        min_context_tokens=2000,
        recommended_context_tokens=4000,
        target_chunk_tokens=1000,
        output_reserve_tokens=250,
        resource_notes="Validates lane outcomes and QA status prior to artifact persistence.",
    ),
}


__all__: list[str] = [
    "COMPOSE_STAGE_PROFILES",
    "ComposeStageProfile",
]
