from __future__ import annotations

import io
import json
from pathlib import Path
from typing import List

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.platform.accounts.models import Organization
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.operations import tasks as op_tasks
from apps.platform.operations.utils import read_job_meta, update_job_meta
from apps.platform.operations.models import LLMConfiguration
from packages.udocket_core.agents.analyze_lib import AnalyzeResult
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
    LLMConfiguration.objects.create(
        organization=org,
        name="Default Analyze",
        target="analyze",
        provider_chain=["azure"],
        stage_map={},
        is_default=True,
    )
    transcript = _make_transcript(settings, str(case.id), str(job.id))
    job.transcript_path = str(transcript)
    job.save(update_fields=["transcript_path"])

    def _write_analyze_outputs(*, case_dir: Path, job_id: str, transcript_path: Path) -> AnalyzeResult:
        analysis_dir = case_dir / "analysis"
        ops_dir = case_dir / "ops"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        ops_dir.mkdir(parents=True, exist_ok=True)

        summary_json_path = analysis_dir / f"{job_id}__summary_v1.json"
        summary_json_path.write_text(json.dumps({"sections": []}), encoding="utf-8")

        summary_md_path = analysis_dir / f"{job_id}__summary_v1.md"
        summary_md_path.write_text("# Summary\n\nThis is a test summary.\n", encoding="utf-8")

        outline_path = analysis_dir / f"{job_id}__outline_v1.json"
        outline_path.write_text(json.dumps({"sections": [{"title": "Intro", "items": []}]}), encoding="utf-8")

        timeline_seed_path = analysis_dir / f"{job_id}__timeline_seeds_v1.json"
        timeline_seed_path.write_text(
            json.dumps(
                {
                    "events": [
                        {
                            "id": "seed-event-1",
                            "uuid": "seed-event-1",
                            "ts_start": 0,
                            "ts_end": None,
                            "speaker": "SPK_1",
                            "text": "Seed",
                            "labels": ["stub"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        entity_hint_path = analysis_dir / f"{job_id}__entity_hints_v1.json"
        entity_hint_path.write_text(
            json.dumps(
                {
                    "entities": [
                        {
                            "id": "entity-1",
                            "uuid": "entity-1",
                            "name": "Test Person",
                            "type": "PERSON",
                            "aliases": [],
                            "mentions": [],
                            "description": "",
                        }
                    ],
                    "relations": [],
                }
            ),
            encoding="utf-8",
        )

        case_brief_path = analysis_dir / f"{job_id}__case_brief_v1.md"
        case_brief_path.write_text("Case brief placeholder", encoding="utf-8")

        meta_path = ops_dir / f"{job_id}__summary_log.json"
        meta_path.write_text(json.dumps({"status": "ok"}, indent=2), encoding="utf-8")

        audit_path = ops_dir / "ops_summary.jsonl"
        with audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"status": "ok", "job_id": job_id}) + "\n")

        return AnalyzeResult(
            status="ok",
            summary_file=summary_json_path,
            summary_markdown_file=summary_md_path,
            outline_file=outline_path,
            timeline_seeds_file=timeline_seed_path,
            entity_hints_file=entity_hint_path,
            case_brief_file=case_brief_path,
            words=5,
            source_transcript=transcript_path,
            meta_json=meta_path,
            audit_jsonl=audit_path,
            provider_chain=["stub"],
        )

    def _fake_analyze_task(*_args, case_id: str, job_id: str, **_kwargs) -> Dict[str, Any]:
        case_dir = tenant_case_root(case_id)
        job = Job.objects.get(pk=job_id)
        result = _write_analyze_outputs(
            case_dir=case_dir,
            job_id=str(job_id),
            transcript_path=Path(job.transcript_path),
        )
        job.status = Job.Status.SUCCEEDED
        job.save(update_fields=["status"])

        meta_payload = {
            "job_kind": "analyze",
            "agent_type": "analyze",
            "summary_status": "completed",
            "summary_file": str(result.summary_file),
            "summary_markdown_file": str(result.summary_markdown_file),
            "summary_outline_file": str(result.outline_file) if result.outline_file else None,
            "summary_timeline_file": str(result.timeline_seeds_file) if result.timeline_seeds_file else None,
            "summary_entity_file": str(result.entity_hints_file) if result.entity_hints_file else None,
            "summary_case_brief_file": str(result.case_brief_file) if result.case_brief_file else None,
            "source_transcript_path": job.transcript_path,
        }
        update_job_meta(str(case_id), job.organization_id, str(job_id), meta_payload)

        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            organization=job.organization,
            job_id=str(job_id),
            type="SUMMARY",
            title="Summary stub",
            path=str(result.summary_file),
            checksum="",
            schema_version="v1",
            metadata={
                "summary_markdown_file": str(result.summary_markdown_file),
                "summary_outline_file": str(result.outline_file),
                "summary_timeline_file": str(result.timeline_seeds_file),
                "summary_entity_file": str(result.entity_hints_file),
            },
        )

        return {
            "status": "ok",
            "job_id": job_id,
            "source_job_id": str(job_id),
            "summary_file": str(result.summary_file),
            "summary_markdown_file": str(result.summary_markdown_file),
            "outline_file": str(result.outline_file) if result.outline_file else None,
            "timeline_file": str(result.timeline_seeds_file) if result.timeline_seeds_file else None,
            "entity_file": str(result.entity_hints_file) if result.entity_hints_file else None,
            "words": result.words,
        }

    def _fake_compose_task(*_args, case_id: str, job_id: str, summary_job_id: str, **_kwargs) -> Dict[str, Any]:
        case_dir = tenant_case_root(case_id)
        analysis_dir = case_dir / "analysis"
        ops_dir = case_dir / "ops"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        ops_dir.mkdir(parents=True, exist_ok=True)

        timeline_file = analysis_dir / f"{job_id}__timeline_v2.json"
        timeline_file.write_text(
            json.dumps(
                {
                    "revision": "v2",
                    "events": [
                        {
                            "id": "compose-event-1",
                            "uuid": "compose-event-1",
                            "title": "Hearing starts",
                            "summary": "Initial call to order",
                            "ts_start": 0,
                            "ts_end": None,
                            "speakers": ["SPK_1"],
                            "references": [],
                            "labels": ["milestone"],
                        }
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        graph_file = analysis_dir / f"{job_id}__graph_v2.json"
        graph_file.write_text(
            json.dumps(
                {
                    "entities": [
                        {
                            "id": "compose-entity-1",
                            "uuid": "compose-entity-1",
                            "name": "Alex Client",
                            "type": "PERSON",
                            "aliases": [],
                            "mentions": [],
                            "description": "",
                        }
                    ],
                    "relationships": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        entities_file = analysis_dir / f"{job_id}__entities_v2.json"
        entities_file.write_text(
            json.dumps(
                {
                    "entities": [
                        {
                            "id": "compose-entity-1",
                            "uuid": "compose-entity-1",
                            "name": "Alex Client",
                            "type": "PERSON",
                            "aliases": [],
                            "mentions": [],
                            "description": "",
                        }
                    ]
                },
                indent=2,
            ),
            encoding="utf-8",
        )
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

        job = Job.objects.get(pk=job_id)
        job.status = Job.Status.SUCCEEDED
        job.save(update_fields=["status"])

        update_job_meta(
            str(case_id),
            job.organization_id,
            str(job_id),
            {
                "compose_status": "completed",
                "timeline_v2_file": str(timeline_file),
                "graph_v2_file": str(graph_file),
                "entities_v2_file": str(entities_file),
                "compose_client_markdown": str(client_md),
                "compose_lawyer_markdown": str(lawyer_md),
            },
        )

        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            organization=job.organization,
            job_id=str(job_id),
            type="COMPOSE",
            title="Compose stub",
            path=str(client_md),
            checksum="",
            schema_version="v1",
            metadata={"format": "markdown"},
        )
        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            organization=job.organization,
            job_id=str(job_id),
            type="TIMELINE",
            title="Timeline stub",
            path=str(timeline_file),
            checksum="",
            schema_version="v2",
            metadata={"schema": "v2"},
        )
        CaseArtifact.objects.create(
            case_id=case_id,
            case_fk=job.case,
            organization=job.organization,
            job_id=str(job_id),
            type="GRAPH",
            title="Graph stub",
            path=str(graph_file),
            checksum="",
            schema_version="v2",
            metadata={"schema": "v2"},
        )

        return {
            "status": "ok",
            "timeline_file": str(timeline_file),
            "graph_file": str(graph_file),
            "client_markdown": str(client_md),
            "lawyer_markdown": str(lawyer_md),
        }

    monkeypatch.setattr(op_tasks.analyze_job, "run", _fake_analyze_task)
    monkeypatch.setattr(op_tasks.compose_job, "run", _fake_compose_task)

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

    out_analyze = op_tasks.analyze_job.run(case_id=str(case.id), job_id=str(job.id))
    if out_analyze is None:
        job.refresh_from_db()
        analyze_meta = read_job_meta(str(case.id), job.organization_id, str(job.id))
        raise AssertionError(
            f"analyze_job returned None (status={job.status}, error={job.error_message}, meta={analyze_meta})"
        )
    assert out_analyze.get("summary_file")

    out_compose = op_tasks.compose_job.run(
        case_id=str(case.id),
        job_id=str(compose_job_obj.id),
        summary_job_id=str(job.id),
    )

    job.refresh_from_db()
    assert job.status == Job.Status.SUCCEEDED
    analysis_dir = tenant_case_root(str(case.id), job.organization_id) / "analysis"
    meta = read_job_meta(str(case.id), job.organization_id, str(job.id))
    if "summary_timeline_file" not in meta:
        pytest.fail(f"meta missing timeline: {meta}")

    def _resolve(key: str, fallback_pattern: str) -> Path:
        path_str = meta.get(key)
        candidates: List[Path] = []
        if path_str:
            candidate = Path(path_str)
            if not candidate.is_absolute():
                candidate = analysis_dir / candidate.name
            if candidate.exists():
                return candidate
        candidates.extend(analysis_dir.glob(fallback_pattern))
        if not candidates:
            raise AssertionError(f"expected path for {key}")
        return sorted(candidates)[0]

    summary_json_path = _resolve("summary_file", f"{job.id}__summary*_v*.json")
    summary_path = _resolve("summary_markdown_file", f"{job.id}__summary*_v*.md")
    timeline_seed_path = _resolve("summary_timeline_file", f"{job.id}__timeline_seeds*_v*.json")
    outline_path = _resolve("summary_outline_file", f"{job.id}__outline*_v*.json")
    entity_hint_path = _resolve("summary_entity_file", f"{job.id}__entity_hints*_v*.json")

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
    timeline_payload = json.loads(timeline_path.read_text(encoding="utf-8"))
    graph_payload = json.loads(graph_path.read_text(encoding="utf-8"))

    assert "events" in seeds_payload
    assert isinstance(seeds_payload["events"], list)
    assert seeds_payload["events"]
    first_seed = seeds_payload["events"][0]
    assert "uuid" in first_seed
    assert first_seed.get("id")

    assert "events" in timeline_payload
    assert isinstance(timeline_payload["events"], list)
    assert timeline_payload["events"], timeline_payload
    first_timeline_event = timeline_payload["events"][0]
    assert first_timeline_event.get("uuid")

    assert "entities" in graph_payload
    if graph_payload["entities"]:
        assert graph_payload["entities"][0].get("uuid")

    arts = list(CaseArtifact.objects.filter(case_id=str(case.id)))
    kinds = sorted(a.type for a in arts)
    assert {"SUMMARY", "TIMELINE", "GRAPH", "COMPOSE"}.issubset(set(kinds))
