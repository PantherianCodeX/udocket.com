from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import pytest

from apps.platform.accounts.models import Organization
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.operations.storage import ensure_case_dirs
from apps.platform.operations import tasks
from packages.udocket_core.agents.analyze_lib import AnalyzeResult


@pytest.mark.django_db
def test_analyze_job_rerun_uses_transcript_and_records_markdown(monkeypatch, settings, tmp_path):
    media_root = tmp_path / "media"
    media_root.mkdir()
    settings.MEDIA_ROOT = str(media_root)

    organization = Organization.objects.create(id="org-1", name="Org One")
    case = Case.objects.create(id="CASE-1", title="Example Case", organization=organization)
    job = Job.objects.create(case=case, organization=organization, audio_input="input.wav")

    case_base = ensure_case_dirs(case.id, organization.id)
    transcript_dir = case_base / "transcript"
    transcript_path = transcript_dir / f"{job.id}__transcript.txt"
    transcript_path.write_text("Transcript text", encoding="utf-8")
    job.transcript_path = str(transcript_path)
    job.save(update_fields=["transcript_path"])

    monkeypatch.setattr(tasks, "_emit_job_update", lambda *_, **__: None)
    monkeypatch.setattr(tasks, "send_case_update", lambda *_, **__: None)
    monkeypatch.setattr(tasks, "audit_emit", lambda *_, **__: None)
    monkeypatch.setattr(
        tasks,
        "load_llm_settings",
        lambda: SimpleNamespace(stage=lambda *_: None, assignments={}),
    )
    monkeypatch.setattr(
        tasks,
        "get_llm_configuration",
        lambda organization_id, config_id, target: {"id": "cfg-1", "provider_chain": ["dummy"], "stage_map": {}},
    )
    monkeypatch.setattr(
        tasks,
        "ensure_default_llm_configuration",
        lambda **_kwargs: {"id": "cfg-1", "provider_chain": ["dummy"], "stage_map": {}},
    )
    monkeypatch.setattr(tasks, "get_provider_secret_with_metadata", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        tasks,
        "collect_requested_providers",
        lambda *_args, **_kwargs: ["dummy"],
        raising=False,
    )

    agent_inputs: list[Path] = []

    def _make_result(call_no: int, input_path: Path, case_dir: Path, job_id: str) -> AnalyzeResult:
        analysis_dir = case_dir / "analysis"
        ops_dir = case_dir / "ops"
        summary_json = analysis_dir / f"{job_id}__summary_v{call_no}.json"
        summary_json.write_text(json.dumps({"call": call_no}), encoding="utf-8")
        summary_md = analysis_dir / f"{job_id}__summary_v{call_no}.md"
        summary_md.write_text(f"# Summary {call_no}\n", encoding="utf-8")
        meta_json = ops_dir / f"{job_id}__summary_meta_v{call_no}.json"
        meta_json.write_text(json.dumps({"token_usage": {"total_tokens": call_no}}), encoding="utf-8")
        audit_jsonl = ops_dir / f"{job_id}__summary_audit_v{call_no}.jsonl"
        audit_jsonl.write_text("{}\n", encoding="utf-8")
        return AnalyzeResult(
            status="ok",
            summary_file=summary_json,
            summary_markdown_file=summary_md,
            outline_file=None,
            timeline_seeds_file=None,
            entity_hints_file=None,
            case_brief_file=None,
            words=call_no * 100,
            source_transcript=input_path,
            meta_json=meta_json,
            audit_jsonl=audit_jsonl,
            provider_chain=["dummy"],
        )

    class DummyAnalyzeAgent:
        def __init__(self, config):
            self.config = config

        def analyze(self, *, input, case_dir, job_id, **_kwargs):
            path_input = Path(input)
            agent_inputs.append(path_input)
            call_no = len(agent_inputs)
            return _make_result(call_no, path_input, Path(case_dir), str(job_id))

    monkeypatch.setattr(tasks, "AnalyzeAgent", DummyAnalyzeAgent)

    tasks.analyze_job.run(case_id=case.id, job_id=str(job.id))
    tasks.analyze_job.run(case_id=case.id, job_id=str(job.id))

    assert agent_inputs[0] == transcript_path
    assert agent_inputs[1] == transcript_path

    job.refresh_from_db()
    assert job.transcript_path == str(transcript_path)

    artifacts = list(
        CaseArtifact.objects.filter(case_id=case.id, type="SUMMARY").order_by("created_at")
    )
    assert len(artifacts) == 2
    latest_artifact = artifacts[-1]
    expected_markdown = case_base / "analysis" / f"{job.id}__summary_v2.md"
    expected_json = case_base / "analysis" / f"{job.id}__summary_v2.json"
    assert latest_artifact.path == str(expected_markdown)
    assert latest_artifact.metadata.get("summary_file") == str(expected_json)
    assert latest_artifact.metadata.get("summary_markdown_file") == str(expected_markdown)
