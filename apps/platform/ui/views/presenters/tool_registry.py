"""Tool panel definitions for case view presenters.

This module centralizes static metadata about interactive case tools so the
presenters can build panel contexts without hard-coding labels, template names,
or capability requirements throughout the codebase. The roadmap calls for a
ToolDefinition registry that typed callers can reference when composing panel
payloads or exposing tooling in other surfaces (API, websocket payloads, etc.).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence


@dataclass(frozen=True)
class ToolDefinition:
    """Immutable description of a case tool panel.

    The definition captures static metadata that the UI needs to render the
    panel header and to route actions to the appropriate backend endpoints.
    Dynamic per-case values (latest job metadata, counts, notes, etc.) remain in
    the presenter logic; the registry simply avoids duplicating the hard-coded
    strings and structural hints across multiple modules.
    """

    key: str
    label: str
    description: str
    body_template: str
    notes_enabled: bool = True
    alerts_key: Optional[str] = None
    llm_target: Optional[str] = None
    job_endpoint_template: Optional[str] = None
    default_actions: Sequence[str] = field(default_factory=tuple)
    artifact_types: Sequence[str] = field(default_factory=tuple)
    data_attributes: Mapping[str, str] = field(default_factory=dict)


_REGISTRY: dict[str, ToolDefinition] = {
    "intake": ToolDefinition(
        key="intake",
        label="Intake",
        description="Manage intake details, assignments, and questionnaire artifacts for this case.",
        body_template="platform_ui/tools/case_details.html",
        notes_enabled=True,
    ),
    "transcribe": ToolDefinition(
        key="transcribe",
        label="Transcribe",
        description="Upload audio or provide a SAS URL to run Azure Speech in Canada-only regions.",
        body_template="platform_ui/tools/transcribe.html",
        notes_enabled=True,
        alerts_key="transcription",
        data_attributes={"data-transcribe": ""},
    ),
    "analyze": ToolDefinition(
        key="analyze",
        label="Analyze",
        description="Generate layered summaries and companion analysis artifacts from approved transcripts.",
        body_template="platform_ui/tools/analyze.html",
        notes_enabled=True,
        alerts_key="analyze",
        llm_target="analyze",
        job_endpoint_template="/api/v1/jobs/{job_id}/analyze/summary/",
        artifact_types=("SUMMARY", "ANALYSIS"),
        data_attributes={"data-analyze": "", "data-llm-target": "analyze"},
    ),
    "compose": ToolDefinition(
        key="compose",
        label="Compose",
        description="Generate client and lawyer-ready deliverables from approved summaries and transcripts.",
        body_template="platform_ui/tools/compose.html",
        notes_enabled=True,
        alerts_key="compose",
        llm_target="compose",
        job_endpoint_template="/api/v1/jobs/{job_id}/analyze/compose/",
        artifact_types=("ANALYSIS", "COMPOSE"),
        data_attributes={"data-compose": "", "data-llm-target": "compose"},
    ),
}


def get_tool_definition(key: str) -> ToolDefinition:
    """Return a registered ToolDefinition.

    Raises:
        KeyError: if the key is unknown. Callers should guard user input before
        requesting a definition.
    """

    return _REGISTRY[key]


def iter_tool_definitions() -> Sequence[ToolDefinition]:
    """Return all known tool definitions in insertion order."""

    return tuple(_REGISTRY.values())


def register_tool_definition(definition: ToolDefinition) -> None:
    """Register a tool definition.

    This helper keeps the registry mutation in one place. In production code the
    registry remains static, but tests may register temporary tools to exercise
    presenter behaviour without touching the module-level state.
    """

    _REGISTRY[definition.key] = definition
