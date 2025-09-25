from __future__ import annotations

import json
import uuid

from django.utils import timezone
from rest_framework.test import APIClient

from apps.platform.accounts.models import Organization, User
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.jobs.models import Job, JobNote
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.operations.storage import ensure_case_dirs, ops_dir
from apps.platform.operations.tasks import _update_job_meta


def _make_case(settings):
    settings.PLATFORM_DEV_OPEN = False
    org = Organization.objects.create(id="ORG-REV", name="Review Org")
    case = Case.objects.create(id="CASE-REV", title="Review Case", organization=org)
    owner = User.objects.create_user(username="owner_rev", password="x", display_name="Owner R")
    reviewer = User.objects.create_user(username="reviewer_rev", password="x", display_name="Reviewer R")
    outsider = User.objects.create_user(username="outsider_rev", password="x")
    CaseMembership.objects.create(case=case, user=owner, role=CaseMembership.Role.OWNER)
    CaseMembership.objects.create(case=case, user=reviewer, role=CaseMembership.Role.REVIEWER)
    case.reviewer = reviewer
    case.save(update_fields=["reviewer"])
    return case, owner, reviewer, outsider


def _make_job(case: Case, *, status: str = Job.Status.SUCCEEDED) -> Job:
    job = Job.objects.create(
        case=case,
        audio_input=f"/tmp/{case.id}-{status}.wav",
        mode=Job.Mode.BATCH,
        diarization=True,
        language="en-CA",
        status=status,
    )
    now = timezone.now()
    job.started_at = now
    job.finished_at = now
    job.duration_s = 12.5
    job.transcript_path = f"/tmp/{job.id}_transcript.txt"
    job.save(update_fields=["started_at", "finished_at", "duration_s", "transcript_path"])
    return job


def test_reviewer_can_approve_and_creates_artifact(db, settings):
    case, owner, reviewer, _ = _make_case(settings)
    job = _make_job(case)
    client = APIClient()
    client.force_authenticate(user=reviewer)

    resp = client.post(f"/api/v1/jobs/{job.id}/approve/")
    assert resp.status_code == 200
    job.refresh_from_db()
    assert job.review_status == Job.ReviewStatus.APPROVED
    assert job.reviewed_by_id == reviewer.id
    assert CaseArtifact.objects.filter(case_id=str(case.id), type="TRANSCRIPT_APPROVED", job_id=str(job.id)).exists()
    payload = resp.json()
    assert payload["review_status"] == "APPROVED"
    assert payload["reviewed_by"] == reviewer.display_name


def test_reviewer_can_reject_and_removes_artifact(db, settings):
    case, owner, reviewer, _ = _make_case(settings)
    job = _make_job(case)
    CaseArtifact.objects.create(
        case_id=str(case.id),
        case_fk=case,
        job_id=str(job.id),
        type="TRANSCRIPT_APPROVED",
        title=f"{job.id}__approval",
        path=job.transcript_path or "",
        checksum="abc",
        schema_version="v1",
        metadata={},
    )
    job.review_status = Job.ReviewStatus.APPROVED
    job.reviewed_by = reviewer
    job.reviewed_at = timezone.now()
    job.save(update_fields=["review_status", "reviewed_by", "reviewed_at"])

    client = APIClient()
    client.force_authenticate(user=reviewer)
    resp = client.post(f"/api/v1/jobs/{job.id}/reject/", {"comment": "needs work"}, format="json")
    assert resp.status_code == 200
    job.refresh_from_db()
    assert job.review_status == Job.ReviewStatus.REJECTED
    assert job.review_comment == "needs work"
    assert not CaseArtifact.objects.filter(case_id=str(case.id), type="TRANSCRIPT_APPROVED", job_id=str(job.id)).exists()


def test_approve_requires_permission(db, settings):
    case, owner, reviewer, outsider = _make_case(settings)
    job = _make_job(case)
    client = APIClient()
    client.force_authenticate(user=outsider)
    resp = client.post(f"/api/v1/jobs/{job.id}/approve/")
    assert resp.status_code in {403, 404}


def test_approve_requires_succeeded_job(db, settings):
    case, owner, reviewer, _ = _make_case(settings)
    job = _make_job(case, status=Job.Status.RUNNING)
    client = APIClient()
    client.force_authenticate(user=reviewer)
    resp = client.post(f"/api/v1/jobs/{job.id}/approve/")
    assert resp.status_code == 400


def test_status_endpoint_includes_review_fields(db, settings):
    case, owner, reviewer, _ = _make_case(settings)
    job = _make_job(case)
    job.review_status = Job.ReviewStatus.APPROVED
    job.reviewed_by = owner
    job.reviewed_at = timezone.now()
    job.review_comment = "looks good"
    job.review_activity_id = uuid.uuid4()
    job.save(update_fields=["review_status", "reviewed_by", "reviewed_at", "review_comment", "review_activity_id"])

    client = APIClient()
    client.force_authenticate(user=owner)
    resp = client.get(f"/api/v1/jobs/{job.id}/status/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["review_status"] == "APPROVED"
    assert data["review_comment"] == "looks good"
    assert data["reviewed_by"] == owner.display_name
    assert data["review_activity_id"] == str(job.review_activity_id)


def test_update_job_meta_merges(db, settings):
    case, owner, reviewer, _ = _make_case(settings)
    job = _make_job(case)
    ops_directory = ops_dir(str(case.id), case.organization_id)
    ops_directory.mkdir(parents=True, exist_ok=True)
    log_path = ops_directory / f"{job.id}_transcription_log.json"
    log_path.write_text(json.dumps({"existing": "value"}), encoding="utf-8")

    _update_job_meta(str(case.id), case.organization_id, str(job.id), {"audio_sha256": "abc", "audio_size_bytes": 1024, "audio_channels": None})
    updated = json.loads(log_path.read_text(encoding="utf-8"))
    assert updated["existing"] == "value"
    assert updated["audio_sha256"] == "abc"
    assert updated["audio_size_bytes"] == 1024
    assert "audio_channels" not in updated  # None filtered out


def test_notes_endpoint_updates_metadata(db, settings):
    case, owner, reviewer, _ = _make_case(settings)
    ensure_case_dirs(str(case.id), case.organization_id)
    job = _make_job(case)
    client = APIClient()
    client.force_authenticate(user=reviewer)

    from django.urls import reverse

    url = reverse('job-notes', args=[job.id])
    resp = client.post(url, {"notes": "Team note"}, format="json")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    notes_payload = body["notes"]
    assert notes_payload["count"] == 1
    entry = notes_payload["entries"][0]
    assert entry["text"] == "Team note"

    resp_second = client.post(url, {"notes": "Follow-up"}, format="json")
    assert resp_second.status_code == 200
    payload_second = resp_second.json()
    assert payload_second["notes"]["count"] == 2
    texts = [item["text"] for item in payload_second["notes"]["entries"]]
    assert "Team note" in texts and "Follow-up" in texts
    assert payload_second["notes"]["entries"][0]["text"] == "Follow-up"

    stored_notes = list(JobNote.objects.filter(job=job).order_by("-created_at"))
    assert len(stored_notes) == 2
    stored_texts = {note.text for note in stored_notes}
    assert {"Team note", "Follow-up"}.issubset(stored_texts)


def test_notes_endpoint_requires_permission(db, settings):
    case, owner, reviewer, outsider = _make_case(settings)
    ensure_case_dirs(str(case.id), case.organization_id)
    job = _make_job(case)
    client = APIClient()
    client.force_authenticate(user=outsider)

    resp = client.post(f"/api/v1/jobs/{job.id}/notes/", {"notes": "should fail"}, format="json")
    assert resp.status_code in {403, 404}
