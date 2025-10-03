from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Dict

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
from packages.udocket_core.agents import guardian_lib
from packages.udocket_core.agents.guardian_lib import GuardianAgent, GuardianConfig
from packages.udocket_core.llm.config import (
    LLMProvider,
    LLMProviderModel,
    LLMSettings,
    LLMStageAssignment,
)


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


def test_guardian_review_builds_runtime_with_provider_object(monkeypatch):
    provider = LLMProvider(
        name="dummy",
        display_name="Dummy",
        models={
            "model-a": LLMProviderModel(
                name="model-a",
                label="Model A",
                cost_tier="standard",
                default_enabled=True,
            )
        },
        api_kind="openai",
        default_endpoint="https://api.example.com",
        requires_api_key=False,
    )
    assignment = LLMStageAssignment(
        stage_key="guardian.review",
        providers=["dummy"],
        model="model-a",
        options={"temperature": "0.0"},
    )
    settings = LLMSettings(providers={"dummy": provider}, assignments={"guardian.review": assignment})

    agent = GuardianAgent(GuardianConfig(provider_chain=["dummy"]), settings=settings)

    captured: Dict[str, object] = {}

    def fake_build_provider_runtime_config(*, provider, model_name, credential_payload, options):
        captured["provider"] = provider
        captured["model_name"] = model_name
        captured["options"] = options
        return SimpleNamespace(
            provider=provider,
            model=SimpleNamespace(name=model_name),
            options=options or {},
            endpoint="https://api.example.com",
            api_key="",
            metadata={},
        )

    class DummyClient:
        def chat(self, messages, temperature, max_tokens):
            captured["messages"] = messages
            captured["temperature"] = temperature
            captured["max_tokens"] = max_tokens
            return json.dumps({"approved": True, "violations": []}), {"total_tokens": 10}

    monkeypatch.setattr(
        guardian_lib,
        "build_provider_runtime_config",
        fake_build_provider_runtime_config,
    )
    monkeypatch.setattr(guardian_lib, "build_chat_client", lambda provider_runtime: DummyClient())

    verdict = agent.review(
        case_id="CASE-1",
        job_id="JOB-1",
        artifact_kind="SUMMARY",
        payload={"content": "ok"},
    )

    assert verdict.approved is True
    assert captured["provider"] is provider
    assert captured["model_name"] == "model-a"
    assert captured["temperature"] == agent.config.temperature
    assert captured["max_tokens"] >= agent.config.max_tokens

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
