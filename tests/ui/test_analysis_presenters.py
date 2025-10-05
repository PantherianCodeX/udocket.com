from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.platform.accounts.models import Organization
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.jobs.models import Job, JobNote
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.ui.views.presenters.analysis_modules import analysis_modules_context
from tests._typing import SettingsFixture


@pytest.mark.django_db()
def test_analysis_modules_include_notes(settings: SettingsFixture):
    settings.PLATFORM_DEV_OPEN = True

    org = Organization.objects.create(name="Analysis Org")
    case = Case.objects.create(id="CASE-ANALYSIS", title="Analysis Case", organization=org)

    user_model = get_user_model()
    user = user_model.objects.create_user(username="analyst", email="analyst@example.com", password="pass")
    CaseMembership.objects.create(case=case, user=user)

    # Transcription job (source)
    job_transcribe = Job.objects.create(
        case=case,
        audio_input="/tmp/audio.wav",
        status=Job.Status.SUCCEEDED,
        transcript_path="/tmp/transcript.txt",
    )

    # Analyze job with note
    job_summary = Job.objects.create(
        case=case,
        audio_input="/tmp/audio.wav",
        status=Job.Status.RUNNING,
    )

    JobNote.objects.create(job=job_summary, text="Needs factual review", created_by=user, created_by_name="Analyst")

    CaseArtifact.objects.create(
        case_id=str(case.id),
        case_fk=case,
        organization=org,
        job_id=str(job_summary.id),
        type="SUMMARY",
        title="Summary Draft",
        path="/tmp/summary.md",
        checksum="",
        schema_version="v1",
        metadata={"source_transcript": "/tmp/transcript.txt"},
    )

    telemetry_map = {
        str(job_transcribe.id): {"metadata": {"job_kind": "transcription"}},
        str(job_summary.id): {
            "metadata": {
                "job_kind": "analyze",
                "summary_file": "/tmp/summary.md",
                "summary_words": 256,
            }
        },
    }

    request = RequestFactory().get(f"/cases/{case.id}/tools/analyze/")
    request.user = user

    modules = analysis_modules_context(
        request=request,
        case=case,
        jobs=[job_transcribe, job_summary],
        telemetry_map=telemetry_map,
    )

    analyze_module = next(module for module in modules if module["key"] == "analyze")
    notes = analyze_module["notes"]

    assert notes["job_id"] == str(job_summary.id)
    assert notes["user_can_add"] is True
    assert notes["entries"]
    assert notes["entries"][0]["text"] == "Needs factual review"
    assert "Needs factual review" in analyze_module["notes_panel"]


@pytest.mark.django_db()
def test_compose_module_lists_extended_deliverables(settings: SettingsFixture, tmp_path):
    settings.PLATFORM_DEV_OPEN = True

    org = Organization.objects.create(name="Compose Org")
    case = Case.objects.create(id="CASE-COMPOSE", title="Compose Case", organization=org)

    user_model = get_user_model()
    user = user_model.objects.create_user(username="composer", email="composer@example.com", password="pass")
    CaseMembership.objects.create(case=case, user=user)

    transcript_job = Job.objects.create(
        case=case,
        audio_input="/tmp/audio.wav",
        status=Job.Status.SUCCEEDED,
        transcript_path="/tmp/transcript.txt",
    )

    summary_job = Job.objects.create(
        case=case,
        audio_input="/tmp/audio.wav",
        status=Job.Status.SUCCEEDED,
    )

    compose_job = Job.objects.create(
        case=case,
        audio_input="/tmp/audio.wav",
        status=Job.Status.SUCCEEDED,
    )

    CaseArtifact.objects.create(
        case_id=str(case.id),
        case_fk=case,
        organization=org,
        job_id=str(summary_job.id),
        type="SUMMARY",
        title="Summary Approved",
        path=str(tmp_path / "summary.json"),
        checksum="",
        schema_version="v1",
    )

    CaseArtifact.objects.create(
        case_id=str(case.id),
        case_fk=case,
        organization=org,
        job_id=str(summary_job.id),
        type="TIMELINE",
        title="Timeline JSON",
        path=str(tmp_path / "timeline.json"),
        checksum="",
        schema_version="v2",
    )

    CaseArtifact.objects.create(
        case_id=str(case.id),
        case_fk=case,
        organization=org,
        job_id=str(summary_job.id),
        type="GRAPH",
        title="Graph JSON",
        path=str(tmp_path / "graph.json"),
        checksum="",
        schema_version="v2",
    )

    compose_artifacts = [
        ("Compose client (MD)", "analysis/JOB__compose_client_v1.md"),
        ("Compose client (DOCX)", "analysis/JOB__compose_client_v1.docx"),
        ("Compose lawyer (MD)", "analysis/JOB__compose_lawyer_v1.md"),
        ("Compose timeline", "analysis/JOB__compose_timeline_v1.md"),
        ("Compose entities", "analysis/JOB__compose_entities_v1.md"),
        ("Compose graph visual", "analysis/JOB__compose_graph_visual_v1.json"),
    ]
    for idx, (title, path) in enumerate(compose_artifacts):
        CaseArtifact.objects.create(
            case_id=str(case.id),
            case_fk=case,
            organization=org,
            job_id=str(compose_job.id),
            type="COMPOSE",
            title=f"{title} #{idx}",
            path=str(tmp_path / path),
            checksum="",
            schema_version="v1",
        )

    telemetry_map = {
        str(transcript_job.id): {"metadata": {"job_kind": "transcription"}},
        str(summary_job.id): {"metadata": {"job_kind": "analyze"}},
        str(compose_job.id): {"metadata": {"job_kind": "compose"}},
    }

    request = RequestFactory().get(f"/cases/{case.id}/tools/compose/")
    request.user = user

    modules = analysis_modules_context(
        request=request,
        case=case,
        jobs=[transcript_job, summary_job, compose_job],
        telemetry_map=telemetry_map,
    )

    compose_module = next(module for module in modules if module["key"] == "compose")
    deliverables = compose_module["latest_details"].get("deliverables", [])
    labels = {item["label"] for item in deliverables}

    assert "Client deliverable (Markdown)" in labels
    assert "Timeline narrative" in labels
    assert "Entity briefing" in labels
    assert "Graph visual embed" in labels

    download_labels = {item["label"] for item in compose_module["downloads"]}
    assert "Timeline narrative" in download_labels