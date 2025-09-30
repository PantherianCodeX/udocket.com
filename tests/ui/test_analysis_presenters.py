from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.platform.accounts.models import Organization
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.jobs.models import Job, JobNote
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.ui.views.presenters.analysis_modules import analysis_modules_context


@pytest.mark.django_db()
def test_analysis_modules_include_notes(settings):
    settings.PLATFORM_DEV_OPEN = True

    org = Organization.objects.create(id="ORG-ANALYSIS", name="Analysis Org")
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

    # Summary job with note
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
                "job_kind": "summary",
                "summary_file": "/tmp/summary.md",
                "summary_words": 256,
            }
        },
    }

    request = RequestFactory().get(f"/cases/{case.id}/tools/summary/")
    request.user = user

    modules = analysis_modules_context(
        request=request,
        case=case,
        jobs=[job_transcribe, job_summary],
        telemetry_map=telemetry_map,
    )

    summary_module = next(module for module in modules if module["key"] == "summary")
    notes = summary_module["notes"]

    assert notes["job_id"] == str(job_summary.id)
    assert notes["user_can_add"] is True
    assert notes["entries"]
    assert notes["entries"][0]["text"] == "Needs factual review"
    assert "Needs factual review" in summary_module["notes_panel"]
