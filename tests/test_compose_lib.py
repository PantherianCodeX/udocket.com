from __future__ import annotations

import json
from pathlib import Path

from packages.udocket_core.agents.compose_lib import (
    ComposeAgent,
    ComposeConfig,
    ComposeResult,
    _normalize_graph_payload,
    _normalize_timeline_payload,
)
from tests._typing import MonkeyPatch


def test_compose_agent_creates_artifacts(tmp_path, monkeypatch: MonkeyPatch):
    case_dir = tmp_path / "case"
    analysis_dir = case_dir / "analysis"
    ops_dir = case_dir / "ops"
    analysis_dir.mkdir(parents=True)
    ops_dir.mkdir(parents=True)

    summary_json = analysis_dir / "summary.json"
    summary_json.write_text(json.dumps({"summary": "Test"}), encoding="utf-8")
    summary_md = analysis_dir / "summary.md"
    summary_md.write_text("# Summary\n\nDetails", encoding="utf-8")

    transcript = analysis_dir / "transcript.txt"
    transcript.write_text("[00:00] SPK_1: Hello", encoding="utf-8")

    agent = ComposeAgent(ComposeConfig(provider_chain=["stub"], debug=True))

    stage_outputs = {
        "compose.context_builder": ({"parties": [], "issues": []}, {"prompt_tokens": 10, "completion_tokens": 5}, "stub"),
        "compose.timeline_builder": ({"revision": "v2", "events": []}, {"prompt_tokens": 8, "completion_tokens": 4}, "stub"),
        "compose.timeline_summary": ("## Key Milestones\n- Item", {"prompt_tokens": 4, "completion_tokens": 3}, "stub"),
        "compose.graph_builder": ({"entities": [], "relationships": []}, {"prompt_tokens": 8, "completion_tokens": 4}, "stub"),
        "compose.entity_brief": ("## Primary Parties\n- Example", {"prompt_tokens": 5, "completion_tokens": 3}, "stub"),
        "compose.graph_visual": (
            {
                "embed_html": "<div></div>",
                "alt_text": "Graph visual summary",
                "notes": "Centered layout",
                "size_hint": {"width": "960px", "height": "640px"},
            },
            {"prompt_tokens": 4, "completion_tokens": 2},
            "stub",
        ),
        "compose.client_brief": ("# Client Brief", {"prompt_tokens": 12, "completion_tokens": 6}, "stub"),
        "compose.lawyer_brief": ("# Lawyer Brief", {"prompt_tokens": 12, "completion_tokens": 6}, "stub"),
        "compose.qa_review": ({"status": "ok"}, {"prompt_tokens": 6, "completion_tokens": 3}, "stub"),
    }

    def fake_invoke_stage(self, **kwargs):  # type: ignore[override]
        key = kwargs["stage_key"]
        return stage_outputs[key]

    monkeypatch.setattr(ComposeAgent, "_invoke_stage", fake_invoke_stage)

    result: ComposeResult = agent.compose(
        case_id="CASE-1",
        case_dir=case_dir,
        job_id="JOB-1",
        summary_json_path=summary_json,
        summary_markdown_path=summary_md,
        transcript_path=transcript,
    )

    assert result.status == "ok"
    artifacts = result.artifacts
    assert artifacts.timeline_file and artifacts.timeline_file.exists()
    assert artifacts.graph_file and artifacts.graph_file.exists()
    assert artifacts.timeline_summary and artifacts.timeline_summary.exists()
    assert artifacts.entity_brief and artifacts.entity_brief.exists()
    assert artifacts.graph_visual_json and artifacts.graph_visual_json.exists()
    assert artifacts.graph_html and artifacts.graph_html.exists()
    assert artifacts.graph_image and artifacts.graph_image.exists()
    assert artifacts.client_markdown and artifacts.client_markdown.exists()
    assert artifacts.lawyer_markdown and artifacts.lawyer_markdown.exists()
    assert artifacts.client_docx and artifacts.client_docx.exists()
    assert artifacts.lawyer_docx and artifacts.lawyer_docx.exists()
    assert result.meta_json.exists()
    assert result.audit_jsonl.exists()


def test_normalize_timeline_payload_preserves_uuid():
    payload = {
        "events": [
            {
                "id": "event-1",
                "uuid": "seed-uuid-123",
                "summary": "Seed",
                "ts_start": 1.23,
                "ts_end": 4.56,
                "speaker": "SPK_1",
                "labels": ["test"],
            }
        ]
    }

    result = _normalize_timeline_payload(payload)
    assert result["events"], result
    normalized = result["events"][0]
    assert normalized["id"] == "event-1"
    assert normalized["uuid"] == "seed-uuid-123"


def test_normalize_graph_payload_preserves_uuid():
    payload = {
        "entities": [
            {
                "id": "entity-1",
                "uuid": "entity-uuid-1",
                "name": "Person A",
                "type": "PERSON",
                "aliases": [],
                "mentions": [],
            }
        ],
        "relationships": [
            {
                "id": "rel-1",
                "uuid": "rel-uuid-1",
                "source": "entity-1",
                "target": "entity-2",
                "type": "ASSOCIATED_WITH",
                "summary": "Worked together",
                "evidence": [
                    {"ts": 12.0, "text": "Reference"},
                ],
            }
        ],
    }

    result = _normalize_graph_payload(payload)
    assert result["entities"], result
    assert result["relationships"], result
    entity = result["entities"][0]
    relation = result["relationships"][0]
    assert entity["uuid"] == "entity-uuid-1"
    assert entity["id"] == "entity-1"
    assert relation["uuid"] == "rel-uuid-1"
    assert relation["id"] == "rel-1"


def test_compose_prompts_include_case_metadata():
    agent = ComposeAgent(ComposeConfig(provider_chain=["stub"], debug=True))

    system_prompt, user_prompt, response_schema = agent._build_prompts(
        stage_key="compose.context_builder",
        transcript_text="",
        summary_markdown="",
        summary_data={},
        timeline_seeds=[],
        entity_hints={},
        staff_report="",
        case_brief={},
        timeline_payload={},
        graph_payload={},
        intake={"court_level": "APPEAL"},
        case_metadata={"case_title": "Example Case", "case_id": "CASE-123"},
        timeline_summary="",
        entity_brief="",
        graph_visual={},
        attachments=[],
        transcript_parse=None,
        profile=None,
        client_markdown="",
        lawyer_markdown="",
    )

    assert "Example Case" in user_prompt
    assert "case_metadata" in user_prompt
