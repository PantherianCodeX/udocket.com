from __future__ import annotations

import json
from pathlib import Path

from packages.udocket_core.agents.compose_lib import ComposeAgent, ComposeConfig, ComposeResult


def test_compose_agent_creates_artifacts(tmp_path, monkeypatch):
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
        "compose.graph_builder": ({"entities": [], "relationships": []}, {"prompt_tokens": 8, "completion_tokens": 4}, "stub"),
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
    assert artifacts.client_markdown and artifacts.client_markdown.exists()
    assert artifacts.lawyer_markdown and artifacts.lawyer_markdown.exists()
    assert artifacts.client_docx and artifacts.client_docx.exists()
    assert artifacts.lawyer_docx and artifacts.lawyer_docx.exists()
    assert result.meta_json.exists()
    assert result.audit_jsonl.exists()

