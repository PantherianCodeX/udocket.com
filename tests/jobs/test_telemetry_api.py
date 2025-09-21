from __future__ import annotations

import json
from pathlib import Path

from django.utils import timezone
from rest_framework.test import APIClient

from apps.platform.accounts.models import Organization, User
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.jobs.models import Job
from apps.platform.operations.storage import ops_dir


def _create_case_with_members(settings):
    settings.PLATFORM_DEV_OPEN = False
    org = Organization.objects.create(id="ORG-TEL", name="Telemetry Org")
    case = Case.objects.create(id="CASE-TEL", title="Telemetry Case", organization=org)
    owner = User.objects.create_user(username="owner_tele", password="x")
    reviewer = User.objects.create_user(username="reviewer_tele", password="x")
    outsider = User.objects.create_user(username="outsider_tele", password="x")
    CaseMembership.objects.create(case=case, user=owner, role=CaseMembership.Role.OWNER)
    CaseMembership.objects.create(case=case, user=reviewer, role=CaseMembership.Role.REVIEWER)
    return case, owner, reviewer, outsider


def _write_ops_payload(case: Case, job: Job, *, with_remote: bool = True) -> None:
    directory = ops_dir(str(case.id), case.organization_id)
    directory.mkdir(parents=True, exist_ok=True)
    meta = {
        "status": job.status,
        "language": job.language,
        "attempts_used": 1,
        "azure_region": "canadacentral",
        "audio_sha256": "local-sha",
        "audio_duration_s": 42.5,
        "sample_rate_hz": 16000,
        "audio_channels": 1,
        "audio_bitrate_kbps": 64,
        "audio_mime": "audio/wav",
        "word_count": 123,
        "transcript_sha256": "transcript-sha",
        "avg_confidence": 0.9123,
        "diarization_enabled": job.diarization,
        "timestamp_utc": "2025-01-01T00:00:00Z",
    }
    if with_remote:
        meta.update({
            "audio_sha256_remote": "remote-sha",
            "audio_content_md5_b64": "abcd==",
            "audio_size_bytes_remote": 1024,
        })

    log_json = directory / f"{job.id}_transcription_log.json"
    log_text = directory / f"{job.id}_transcription.log"
    log_json.write_text(json.dumps(meta), encoding="utf-8")
    log_text.write_text("line one\nline two\n", encoding="utf-8")


def _create_job(case: Case, *, status: str = Job.Status.SUCCEEDED) -> Job:
    job = Job.objects.create(
        case=case,
        audio_input=f"/tmp/{case.id}_{status}.wav",
        mode=Job.Mode.BATCH,
        diarization=True,
        language="en-CA",
        status=status,
    )
    now = timezone.now()
    job.started_at = now
    job.finished_at = now
    job.duration_s = 10.5
    job.transcript_path = f"/tmp/{job.id}_transcript.txt"
    job.save(update_fields=["started_at", "finished_at", "duration_s", "transcript_path"])
    _write_ops_payload(case, job)
    return job


def test_job_detail_endpoint_returns_full_telemetry(db, settings):
    case, owner, reviewer, _ = _create_case_with_members(settings)
    job = _create_job(case)

    client = APIClient()
    client.force_authenticate(user=owner)
    resp = client.get(f"/api/v1/jobs/{job.id}/detail/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(job.id)
    assert data["audio"]["path"] == job.audio_input
    assert data["transcript"]["path"] == job.transcript_path
    assert data["agent"]["region"] == "canadacentral"
    assert data["artifacts"] and data["artifacts"][0]["download_url"]
    assert "line two" in data["log_excerpt"]


def test_job_detail_endpoint_hides_paths_without_download_cap(db, settings):
    case, owner, reviewer, _ = _create_case_with_members(settings)
    job = _create_job(case)

    client = APIClient()
    client.force_authenticate(user=reviewer)
    resp = client.get(f"/api/v1/jobs/{job.id}/detail/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["audio"]["path"] is None
    assert data["transcript"] is None or data["transcript"].get("path") is None
    assert not any((artifact.get("download_url") for artifact in data.get("artifacts", [])))


def test_case_jobs_summary_and_detail_endpoints(db, settings):
    case, owner, reviewer, outsider = _create_case_with_members(settings)
    succeeded = _create_job(case, status=Job.Status.SUCCEEDED)
    running = _create_job(case, status=Job.Status.RUNNING)

    client = APIClient()
    client.force_authenticate(user=owner)

    summary_resp = client.get(f"/api/v1/cases/{case.id}/jobs/summary/")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["total"] == 2
    assert summary["succeeded"] == 1
    assert summary["running"] == 1
    assert summary["failed"] == 0
    assert summary["pending"] == 0

    detail_resp = client.get(f"/api/v1/cases/{case.id}/jobs/detail/")
    assert detail_resp.status_code == 200
    jobs = detail_resp.json()["jobs"]
    ids = {job_info["id"] for job_info in jobs}
    assert ids == {str(succeeded.id), str(running.id)}

    client.force_authenticate(user=outsider)
    forbidden = client.get(f"/api/v1/cases/{case.id}/jobs/summary/")
    assert forbidden.status_code == 403
