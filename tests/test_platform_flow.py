from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.platform.accounts.models import Organization
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.operations import tasks as op_tasks
from packages.udocket_core.agents.summarize_lib import SummarizeAgent, SummarizeResult
from apps.platform.operations.storage import tenant_case_root


@pytest.fixture(autouse=True)
def _is_dev_open(settings, tmp_path):
    settings.PLATFORM_DEV_OPEN = True
    settings.MEDIA_ROOT = str(tmp_path / "media")
    return settings


def test_jobs_upload_file_creates_job_and_saves_file(db, settings):
    org = Organization.objects.create(id="ORG-FLOW1", name="Flow Org 1")
    case = Case.objects.create(id="CASE-T1", title="Upload Test", organization=org)
    client = APIClient()

    audio_bytes = b"RIFF....WAVEfmt "  # minimal header-ish; we only check file persisted
    file = SimpleUploadedFile("sample.wav", audio_bytes, content_type="audio/wav")

    # Avoid executing Celery task (no Azure in tests)
    from apps.platform.operations import tasks

    called = {"n": 0}

    def _noop(**kwargs):
        called["n"] += 1
        return {"status": "queued"}

    orig = tasks.transcribe_job.delay
    tasks.transcribe_job.delay = _noop  # type: ignore
    try:
        resp = client.post(
            "/api/v1/jobs/upload/",
            data={"case": case.id, "audio": file, "mode": Job.Mode.ON_DEMAND},
            format="multipart",
        )
    finally:
        tasks.transcribe_job.delay = orig  # type: ignore

    assert resp.status_code == 201
    data = resp.json()
    job_id = data["id"]
    job = Job.objects.get(pk=job_id)
    assert Path(job.audio_input).exists()
    assert called["n"] == 1


def _make_transcript(settings, case_id: str, job_id: str) -> Path:
    base = tenant_case_root(case_id)
    tdir = base / "transcript"
    tdir.mkdir(parents=True, exist_ok=True)
    p = tdir / f"{job_id}__transcript.txt"
    p.write_text(
        "\n".join(
            [
                "[00:00] SPK_1: Good morning everyone.",
                "[00:05] SPK_2: Good morning.",
                "[00:10] SPK_1: Let's begin the hearing.",
            ]
        ),
        encoding="utf-8",
    )
    return p


def test_analysis_tasks_generate_artifacts(db, settings, monkeypatch):
    org = Organization.objects.create(id="ORG-FLOW2", name="Flow Org 2")
    case = Case.objects.create(id="CASE-T2", title="Analysis Test", organization=org)
    job = Job.objects.create(case=case, audio_input="/tmp/a.wav")
    transcript = _make_transcript(settings, str(case.id), str(job.id))
    job.transcript_path = str(transcript)
    job.save(update_fields=["transcript_path"])

    def _stub_summarize(self, **kwargs):
        case_dir = Path(kwargs["case_dir"])
        job_id = kwargs["job_id"]
        analysis_dir = case_dir / "analysis"
        ops_dir = case_dir / "ops"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        ops_dir.mkdir(parents=True, exist_ok=True)

        summary_path = analysis_dir / f"{job_id}__summary_v1.md"
        summary_path.write_text("# Summary\n\nThis is a test summary.\n", encoding="utf-8")

        outline_path = analysis_dir / f"{job_id}__outline_v1.json"
        outline_payload = {"sections": [{"title": "Intro", "items": []}]}
        outline_path.write_text(json.dumps(outline_payload, indent=2), encoding="utf-8")

        timeline_path = analysis_dir / f"{job_id}__timeline_seed_v1.json"
        timeline_events = [
            {
                "ts_start": 0,
                "ts_end": None,
                "speaker": "SPK_1",
                "text": "This is a timeline seed",
                "labels": [],
            }
        ]
        timeline_path.write_text(json.dumps({"events": timeline_events}, indent=2), encoding="utf-8")

        entity_path = analysis_dir / f"{job_id}__entity_hints_v1.json"
        entity_payload = {
            "entities": [
                {
                    "id": "E1",
                    "name": "Person A",
                    "type": "PERSON",
                    "mentions": [{"ts": 0, "text": "Person A"}],
                }
            ]
        }
        entity_path.write_text(json.dumps(entity_payload, indent=2), encoding="utf-8")

        case_brief_path = analysis_dir / f"{job_id}__case_brief_v1.md"
        case_brief_path.write_text("Case brief placeholder", encoding="utf-8")

        meta_path = analysis_dir / f"{job_id}__summary_meta.json"
        meta_path.write_text(json.dumps({"status": "ok"}, indent=2), encoding="utf-8")

        audit_path = ops_dir / f"{job_id}__summary_audit.jsonl"
        audit_path.write_text(json.dumps({"status": "ok"}) + "\n", encoding="utf-8")

        return SummarizeResult(
            status="ok",
            summary_file=summary_path,
            summary_markdown_file=summary_path,
            outline_file=outline_path,
            timeline_seeds_file=timeline_path,
            entity_hints_file=entity_path,
            case_brief_file=case_brief_path,
            words=5,
            source_transcript=Path(kwargs["input"]),
            meta_json=meta_path,
            audit_jsonl=audit_path,
            provider_chain=["stub"],
        )

    monkeypatch.setattr(SummarizeAgent, "summarize", _stub_summarize)

    # Call task functions directly (avoid Celery runtime)
    out1 = op_tasks.summarize_job.run(None, case_id=str(case.id), job_id=str(job.id))
    out2 = op_tasks.timeline_job.run(None, case_id=str(case.id), job_id=str(job.id))
    out3 = op_tasks.graph_job.run(None, case_id=str(case.id), job_id=str(job.id))

    summary_path = Path(out1["summary_file"])
    timeline_seed_path = Path(out1["timeline_file"])
    outline_path = Path(out1["outline_file"])
    entity_hint_path = Path(out1["entity_file"])
    timeline_path = Path(out2["timeline_file"])
    entities_path = Path(out3["entities_file"])
    graph_path = Path(out3["graph_file"])

    assert summary_path.exists()
    assert outline_path.exists()
    assert timeline_seed_path.exists()
    assert entity_hint_path.exists()
    assert timeline_path.exists()
    assert entities_path.exists()
    assert graph_path.exists()

    seeds_payload = json.loads(timeline_seed_path.read_text(encoding="utf-8"))
    timeline_events = json.loads(timeline_path.read_text(encoding="utf-8"))
    if isinstance(seeds_payload, dict):
        seeds_events = seeds_payload.get("events", [])
    else:
        seeds_events = seeds_payload
    assert timeline_events == seeds_events

    hints = json.loads(entity_hint_path.read_text(encoding="utf-8"))
    entity_payload = json.loads(entities_path.read_text(encoding="utf-8"))
    graph_payload = json.loads(graph_path.read_text(encoding="utf-8"))

    hint_names = {
        ent.get("name")
        for ent in hints.get("entities", [])
        if isinstance(ent, dict) and ent.get("name")
    }
    produced_names = {
        ent.get("name")
        for ent in entity_payload.get("entities", [])
        if isinstance(ent, dict) and ent.get("name")
    }
    assert hint_names <= produced_names
    assert len(graph_payload.get("nodes", [])) == len(produced_names)

    arts = list(CaseArtifact.objects.filter(case_id=str(case.id)))
    kinds = sorted(a.type for a in arts)
    assert set(kinds) >= {"SUMMARY", "TIMELINE", "ENTITIES", "GRAPH"}
