from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import json

import pytest

from apps.platform.accounts.models import Organization
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.operations.storage import ensure_case_dirs, ops_dir as storage_ops_dir
from apps.platform.operations import tasks


@pytest.mark.django_db
def test_timeline_job_requires_summary_seeds(monkeypatch, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    organization = Organization.objects.create(id="org-ops", name="Org Ops")
    case = Case.objects.create(id="CASE-TL", title="Timeline Case", organization=organization)
    job = Job.objects.create(case=case, organization=organization, audio_input="/tmp/audio.wav")
    transcript = tmp_path / "transcript.txt"
    transcript.write_text("[00:00] Speaker: Hello", encoding="utf-8")
    job.transcript_path = str(transcript)
    job.save(update_fields=["transcript_path"])

    ensure_case_dirs(case.id, organization.id)

    monkeypatch.setattr(tasks, "TimelineAgent", lambda *_args, **_kwargs: SimpleNamespace(build=lambda **kwargs: None))

    with pytest.raises(RuntimeError) as exc:
        tasks.timeline_job.run(case_id=case.id, job_id=str(job.id))
    assert "Summary timeline seeds" in str(exc.value)


@pytest.mark.django_db
def test_graph_job_requires_entity_hints(monkeypatch, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    organization = Organization.objects.create(id="org-ops", name="Org Ops")
    case = Case.objects.create(id="CASE-GR", title="Graph Case", organization=organization)
    job = Job.objects.create(case=case, organization=organization, audio_input="/tmp/audio.wav")
    transcript = tmp_path / "transcript-graph.txt"
    transcript.write_text("[00:00] Speaker: Hello", encoding="utf-8")
    job.transcript_path = str(transcript)
    job.save(update_fields=["transcript_path"])

    ensure_case_dirs(case.id, organization.id)

    monkeypatch.setattr(tasks, "GraphAgent", lambda *_args, **_kwargs: SimpleNamespace(build=lambda **kwargs: None))

    with pytest.raises(RuntimeError) as exc:
        tasks.graph_job.run(case_id=case.id, job_id=str(job.id))
    assert "Summary entity hints" in str(exc.value)


@pytest.mark.django_db
def test_timeline_job_uses_seed_artifacts(monkeypatch, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    organization = Organization.objects.create(id="org-ops", name="Org Ops")
    case = Case.objects.create(id="CASE-TL2", title="Timeline Case", organization=organization)
    job = Job.objects.create(case=case, organization=organization, audio_input="/tmp/audio.wav")
    transcript_dir = ensure_case_dirs(case.id, organization.id) / "transcript"
    transcript_path = transcript_dir / f"{job.id}__transcript.txt"
    transcript_path.write_text("[00:00] Speaker: Hello", encoding="utf-8")
    job.transcript_path = str(transcript_path)
    job.save(update_fields=["transcript_path"])

    analysis_dir = transcript_dir.parent / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    seeds_path = analysis_dir / f"{job.id}__timeline_seeds.json"
    seeds_path.write_text(json.dumps({"events": [{"ts_start": 0, "text": "Hi"}]}), encoding="utf-8")

    ops_dir = storage_ops_dir(case.id, organization.id)
    meta_path = ops_dir / f"{job.id}_transcription_log.json"
    meta_path.write_text(json.dumps({"summary_timeline_file": str(seeds_path)}), encoding="utf-8")

    captured = {}

    class DummyTimelineAgent:
        def __init__(self, *_args, **_kwargs) -> None:
            self.config = SimpleNamespace(schema_version="v1")

        def build(self, **kwargs):
            captured.update(kwargs)
            timeline_file = analysis_dir / f"{job.id}__timeline_v1.json"
            timeline_file.write_text("[]", encoding="utf-8")
            return SimpleNamespace(
                timeline_file=timeline_file,
                events=[{"id": "event"}],
                checksum="abc123",
                source_transcript=transcript_path,
                seed_source=seeds_path,
            )

    monkeypatch.setattr(tasks, "TimelineAgent", DummyTimelineAgent)
    monkeypatch.setattr(tasks, "send_case_update", lambda *args, **kwargs: None)
    monkeypatch.setattr(tasks, "audit_emit", lambda *args, **kwargs: None)

    result = tasks.timeline_job.run(case_id=case.id, job_id=str(job.id))

    assert result["status"] == "ok"
    assert captured["seed_path"] == seeds_path
    assert captured["seed_events"]


@pytest.mark.django_db
def test_graph_job_uses_entity_hints(monkeypatch, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    organization = Organization.objects.create(id="org-ops", name="Org Ops")
    case = Case.objects.create(id="CASE-GR2", title="Graph Case", organization=organization)
    job = Job.objects.create(case=case, organization=organization, audio_input="/tmp/audio.wav")
    transcript_dir = ensure_case_dirs(case.id, organization.id) / "transcript"
    transcript_path = transcript_dir / f"{job.id}__transcript.txt"
    transcript_path.write_text("[00:00] Speaker: Hello", encoding="utf-8")
    job.transcript_path = str(transcript_path)
    job.save(update_fields=["transcript_path"])

    analysis_dir = transcript_dir.parent / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    hints_path = analysis_dir / f"{job.id}__entity_hints.json"
    hints_path.write_text(json.dumps({"entities": ["person"]}), encoding="utf-8")

    ops_dir = storage_ops_dir(case.id, organization.id)
    meta_path = ops_dir / f"{job.id}_transcription_log.json"
    meta_path.write_text(json.dumps({"summary_entity_file": str(hints_path)}), encoding="utf-8")

    captured = {}

    class DummyGraphAgent:
        def __init__(self, *_args, **_kwargs) -> None:
            self.config = SimpleNamespace(schema_version="v1")

        def build(self, **kwargs):
            captured.update(kwargs)
            graph_file = analysis_dir / f"{job.id}__graph_v1.json"
            entities_file = analysis_dir / f"{job.id}__entities_v1.json"
            graph_file.write_text("{}", encoding="utf-8")
            entities_file.write_text("[]", encoding="utf-8")
            return SimpleNamespace(
                graph_file=graph_file,
                entities=[{"id": "entity"}],
                edges=[],
                checksum="def456",
                source_transcript=transcript_path,
                hint_source=hints_path,
                entities_file=entities_file,
                entities_checksum="abc111",
                graph_checksum="def222",
            )

    monkeypatch.setattr(tasks, "GraphAgent", DummyGraphAgent)
    monkeypatch.setattr(tasks, "send_case_update", lambda *args, **kwargs: None)
    monkeypatch.setattr(tasks, "audit_emit", lambda *args, **kwargs: None)

    result = tasks.graph_job.run(case_id=case.id, job_id=str(job.id))

    assert result["status"] == "ok"
    assert captured["hint_path"] == hints_path
    assert captured["hint_payload"] == {"entities": ["person"]}
    assert CaseArtifact.objects.filter(case_id=case.id, type="GRAPH").exists()
