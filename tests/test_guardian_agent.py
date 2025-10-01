from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.platform.accounts.models import Organization
from apps.platform.operations.guardian import (
    snapshot_artifact_for_guardian,
    get_guardian_instructions,
    save_guardian_instructions,
    new_instruction_template,
    build_guardian_context,
)
from apps.platform.artifacts.models import CaseArtifact
from packages.udocket_core.agents.guardian_lib import GuardianAgent, GuardianConfig


def test_guardian_parse_verdict_includes_citations():
    agent = GuardianAgent(GuardianConfig())
    raw = json.dumps(
        {
            "approved": False,
            "notes": "Contains advice",
            "remediation": "Remove legal guidance",
            "violations": [
                {
                    "category": "legal_advice",
                    "message": "Advises on legal strategy",
                    "severity": "high",
                    "citation": "paragraph 3",
                    "recommendation": "Rewrite as factual summary",
                }
            ],
        }
    )

    verdict = agent._parse_verdict(  # pylint: disable=protected-access
        raw_response=raw,
        provider="azure",
        model="gpt-4o-mini",
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    )

    assert verdict.approved is False
    assert verdict.remediation == "Remove legal guidance"
    assert verdict.violations[0]["citation"] == "paragraph 3"
    assert verdict.violations[0]["recommendation"] == "Rewrite as factual summary"


def test_snapshot_artifact_reads_text(tmp_path):
    text_path = tmp_path / "sample_summary.md"
    text_path.write_text("Example summary content", encoding="utf-8")

    artifact = CaseArtifact(
        id=1,
        case_id="CASE-1",
        type="summary",
        title="Summary",
        path=str(text_path),
        checksum="",
        organization_id=1,
    )

    snapshot = snapshot_artifact_for_guardian(artifact)

    assert snapshot["path"] == str(text_path)
    assert "content" in snapshot
    assert snapshot["content"].startswith("Example summary")


@pytest.mark.django_db
def test_guardian_instructions_defaults():
    org = Organization.objects.create(id="guardian-org", name="Guardian Org")

    instructions = get_guardian_instructions(str(org.id))

    assert instructions
    assert any(entry.get("title") for entry in instructions)

    template = new_instruction_template()
    template.update(
        {
            "title": "Summaries",
            "text": "Focus on summaries",
            "applies_to": ["SUMMARY"],
            "severity": "high",
        }
    )
    instructions.append(template)
    save_guardian_instructions(str(org.id), instructions)

    updated = get_guardian_instructions(str(org.id))
    assert any(entry.get("id") == template["id"] for entry in updated)


@pytest.mark.django_db
def test_build_guardian_context_includes_instructions():
    org = Organization.objects.create(id="context-org", name="Context Org")

    context = build_guardian_context(str(org.id))

    assert context is not None
    assert context.instructions
