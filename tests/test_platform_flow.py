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
from apps.platform.operations.utils import update_job_meta
from packages.udocket_core.agents.compose_lib import ComposeAgent, ComposeResult, ComposeArtifacts
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

    def _stub_compose(self, **kwargs):
        case_dir = Path(kwargs["case_dir"])
        job_id = kwargs["job_id"]
        analysis_dir = case_dir / "analysis"
        ops_dir = case_dir / "ops"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        ops_dir.mkdir(parents=True, exist_ok=True)

        timeline_file = analysis_dir / f"{job_id}__timeline_v2.json"
        timeline_file.write_text(json.dumps({"revision": "v2", "events": []}, indent=2), encoding="utf-8")
        graph_file = analysis_dir / f"{job_id}__graph_v2.json"
        graph_file.write_text(json.dumps({"entities": [], "relationships": []}, indent=2), encoding="utf-8")
        entities_file = analysis_dir / f"{job_id}__entities_v2.json"
        entities_file.write_text(json.dumps({"entities": []}, indent=2), encoding="utf-8")
        client_md = analysis_dir / f"{job_id}__compose_client_v1.md"
        client_md.write_text("# Client", encoding="utf-8")
        lawyer_md = analysis_dir / f"{job_id}__compose_lawyer_v1.md"
        lawyer_md.write_text("# Lawyer", encoding="utf-8")
        client_docx = analysis_dir / f"{job_id}__compose_client_v1.docx"
        client_docx.write_bytes(b"PK\x03\x04")
        lawyer_docx = analysis_dir / f"{job_id}__compose_lawyer_v1.docx"
        lawyer_docx.write_bytes(b"PK\x03\x04")
        meta_json = ops_dir / f"{job_id}__compose_log.json"
        meta_json.write_text(json.dumps({"status": "ok"}, indent=2), encoding="utf-8")
        audit_jsonl = ops_dir / "ops_compose.jsonl"
        audit_jsonl.write_text(json.dumps({"status": "ok"}) + "\n", encoding="utf-8")

        artifacts = ComposeArtifacts(
            timeline_file=timeline_file,
            graph_file=graph_file,
            entities_file=entities_file,
            client_markdown=client_md,
            lawyer_markdown=lawyer_md,
            client_docx=client_docx,
            lawyer_docx=lawyer_docx,
        )
        return ComposeResult(
            status="ok",
            artifacts=artifacts,
            meta_json=meta_json,
            audit_jsonl=audit_jsonl,
            provider_chain=["stub"],
            stage_usage={}
        )

    monkeypatch.setattr(ComposeAgent, "compose", _stub_compose)

    # Call task functions directly (avoid Celery runtime)
    analysis_dir = tenant_case_root(str(case.id)) / "analysis"
    ops_dir = tenant_case_root(str(case.id)) / "ops"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    ops_dir.mkdir(parents=True, exist_ok=True)

    summary_json_path = analysis_dir / f"{job.id}__summary_v1.json"
    summary_json_path.write_text(json.dumps({"sections": []}), encoding="utf-8")

    summary_md_path = analysis_dir / f"{job.id}__summary_v1.md"
    summary_md_path.write_text("# Summary\n\nThis is a test summary.\n", encoding="utf-8")

    outline_path = analysis_dir / f"{job.id}__outline_v1.json"
    outline_path.write_text(json.dumps({"sections": [{"title": "Intro", "items": []}]}), encoding="utf-8")

    timeline_seed_path = analysis_dir / f"{job.id}__timeline_seeds_v1.json"
    timeline_seed_path.write_text(json.dumps({"events": [{"ts_start": 0, "ts_end": None, "speaker": "SPK_1", "text": "Seed"}]}), encoding="utf-8")

    entity_hint_path = analysis_dir / f"{job.id}__entity_hints_v1.json"
    entity_hint_path.write_text(json.dumps({"entities": []}), encoding="utf-8")

    case_brief_path = analysis_dir / f"{job.id}__case_brief_v1.md"
    case_brief_path.write_text("Case brief placeholder", encoding="utf-8")

    update_job_meta(
        str(case.id),
        org.id,
        str(job.id),
        {
            "summary_status": "completed",
            "summary_file": str(summary_json_path),
            "summary_markdown_file": str(summary_md_path),
            "summary_outline_file": str(outline_path),
            "summary_timeline_file": str(timeline_seed_path),
            "summary_entity_file": str(entity_hint_path),
            "summary_case_brief_file": str(case_brief_path),
            "source_transcript_path": job.transcript_path,
        },
    )

    compose_job_obj = Job.objects.create(
        case=case,
        organization=org,
        audio_input=job.audio_input,
        mode=job.mode,
        diarization=job.diarization,
        language=job.language,
        transcript_path=job.transcript_path,
        duration_s=job.duration_s,
    )

    out_compose = op_tasks.compose_job.run(
        None,
        case_id=str(case.id),
        job_id=str(compose_job_obj.id),
        summary_job_id=str(job.id),
    )

    analysis_dir = tenant_case_root(str(case.id)) / "analysis"
    summary_json_candidates = list(analysis_dir.glob(f"{job.id}__summary*_v1.json"))
    if not summary_json_candidates:
        summary_json_candidates = list(analysis_dir.glob(f"{job.id}__summary*.json"))
    if not summary_json_candidates:
        summary_json_candidates = list(analysis_dir.glob("*summary*.json"))
    summary_json_path = summary_json_candidates[0]

    summary_markdown_candidates = list(analysis_dir.glob(f"{job.id}__summary*_v1.md"))
    if not summary_markdown_candidates:
        summary_markdown_candidates = list(analysis_dir.glob("*summary*.md"))
    summary_path = summary_markdown_candidates[0]
    timeline_seed_candidates = list(analysis_dir.glob("*__timeline_seeds_v1.json"))
    assert timeline_seed_candidates
    timeline_seed_path = timeline_seed_candidates[0]

    outline_candidates = list(analysis_dir.glob("*__outline_v1.json"))
    assert outline_candidates
    outline_path = outline_candidates[0]

    entity_hint_candidates = list(analysis_dir.glob("*__entity_hints_v1.json"))
    assert entity_hint_candidates
    entity_hint_path = entity_hint_candidates[0]

    timeline_path = Path(out_compose["timeline_file"])
    graph_path = Path(out_compose["graph_file"])
    entities_path = analysis_dir / f"{compose_job_obj.id}__entities_v2.json"

    produced_files = {p.name for p in analysis_dir.glob('*')}
    assert summary_path.exists(), produced_files
    assert summary_json_path.exists()
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
    seeds_payload = json.loads(timeline_seed_path.read_text(encoding="utf-8"))
    assert "events" in seeds_payload
    assert json.loads(timeline_path.read_text(encoding="utf-8"))
    assert json.loads(graph_path.read_text(encoding="utf-8"))

    arts = list(CaseArtifact.objects.filter(case_id=str(case.id)))
    kinds = sorted(a.type for a in arts)
    assert {"SUMMARY", "TIMELINE", "GRAPH", "COMPOSE"}.issubset(set(kinds))
