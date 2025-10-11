# pyright: strict

"""Compose agent support modules.

This package currently exposes stage profile metadata used by the UI when
rendering LLM configuration controls for the Compose tool. As the Compose agent
pipeline is implemented, additional helpers (configs, orchestrators, etc.) will
live here to keep the contract aligned with root AGENTS guidelines.
"""

from .errors import ComposeStageError, ComposeStageContext
from .profiles import COMPOSE_STAGE_PROFILES, ComposeStageProfile
from .settings import ComposeConfig, DEFAULT_PROVIDER_CHAIN, DOC_TEMPLATE_ENV, normalize_provider_chain
from .context import assemble_context, serialize_context
from .io import (
    ArtifactWriter,
    build_bundle,
    docx_placeholder_context,
    markdown_paragraphs,
    markdown_to_subdoc,
    render_docx_from_template,
    render_qa_markdown,
)
from .state import (
    ComposeArtifacts,
    ComposeContext,
    ComposeInputs,
    ComposeResult,
    ComposeState,
    GuardReport,
    LaneActionDirective,
    LaneAttempt,
    LaneOutcome,
    LaneRuntimeState,
    QAReviewerResult,
    clone_guard_report,
    compose_context_to_json,
    compose_inputs_to_json,
    guard_report_to_json,
    lane_action_to_json,
    lane_attempt_to_json,
    lane_history_payload,
    lane_outcome_to_json,
    lane_runtime_state_to_json,
    qa_result_to_json,
    serialize_compose_state,
)
from .guards import (
    compliance_report,
    factuality_report,
    markdown_structure_report,
    sentence_length_report,
)
from .qa import run_qa_review
from .run import ComposeRun

__all__: list[str] = [
    "COMPOSE_STAGE_PROFILES",
    "ComposeStageProfile",
    "ComposeStageContext",
    "ComposeStageError",
    "ComposeConfig",
    "DEFAULT_PROVIDER_CHAIN",
    "DOC_TEMPLATE_ENV",
    "normalize_provider_chain",
    "ComposeArtifacts",
    "ComposeContext",
    "ComposeInputs",
    "ComposeResult",
    "ComposeState",
    "GuardReport",
    "LaneActionDirective",
    "LaneAttempt",
    "LaneOutcome",
    "LaneRuntimeState",
    "QAReviewerResult",
    "clone_guard_report",
    "lane_history_payload",
    "guard_report_to_json",
    "lane_attempt_to_json",
    "lane_outcome_to_json",
    "lane_runtime_state_to_json",
    "lane_action_to_json",
    "qa_result_to_json",
    "compose_inputs_to_json",
    "compose_context_to_json",
    "serialize_compose_state",
    "assemble_context",
    "serialize_context",
    "ArtifactWriter",
    "build_bundle",
    "docx_placeholder_context",
    "markdown_paragraphs",
    "markdown_to_subdoc",
    "render_docx_from_template",
    "render_qa_markdown",
    "ComposeRun",
    "run_qa_review",
    "compliance_report",
    "factuality_report",
    "markdown_structure_report",
    "sentence_length_report",
]
