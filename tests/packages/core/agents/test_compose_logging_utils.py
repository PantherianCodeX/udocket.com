from __future__ import annotations

from packages.core.agents.compose.logging_utils import (
    ComposeLogContext,
    format_run_message,
    format_stage_message,
    friendly_stage_label,
)


def test_friendly_stage_label_lane_stage() -> None:
    context = ComposeLogContext(case_id="case-1", job_id="job-1")
    label = friendly_stage_label("compose.client.draft")
    assert label == "client draft"

    message = format_stage_message(
        context,
        stage="compose.client.draft",
        event="start",
        details={"attempt": 1, "lane": "client"},
    )
    assert "Compose agent starting client draft" in message
    assert "attempt 1" in message


def test_format_stage_message_complete_includes_provider_and_counts() -> None:
    context = ComposeLogContext(case_id="case-2", job_id="job-2", case_title="Case Two")
    message = format_stage_message(
        context,
        stage="compose.client.qa_reviewer",
        event="complete",
        details={
            "attempt": 2,
            "lane": "client",
            "provider": "openai",
            "model": "gpt-5",
            "warnings": ["drift"],
        },
    )
    assert "finished client QA review" in message
    assert "warnings=1" in message
    assert "via openai:gpt-5" in message


def test_format_run_message_for_snapshot_events() -> None:
    context = ComposeLogContext(case_id="case-3", job_id="job-3")
    snapshot_message = format_run_message(
        context,
        "compose.run.snapshot_recorded",
        {"sequence": 5, "stage": "compose.client.revise", "path": "0005_compose-client-revise.json"},
    )
    assert "Saved compose snapshot #5" in snapshot_message
    assert "client revision" in snapshot_message

    manifest_failure = format_run_message(
        context,
        "compose.run.manifest_read_failed",
        {"path": "missing.json"},
    )
    assert "Failed reading compose manifest" in manifest_failure
