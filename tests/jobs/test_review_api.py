# pyright: reportUnnecessaryCast=false
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Protocol, Sequence, Type, TypeVar, cast

from django.utils import timezone  # type: ignore[reportMissingImports]
from rest_framework.test import APIClient as _APIClient  # type: ignore[reportMissingImports]

from apps.platform.accounts.models import Organization, User
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.jobs.models import Job, JobNote
from apps.platform.operations.storage import ensure_case_dirs, ops_dir
from apps.platform.operations.utils import update_job_meta

APPROVED_REVIEW_STATUS = cast(str, getattr(Job.ReviewStatus, "APPROVED", "APPROVED"))
REJECTED_REVIEW_STATUS = cast(str, getattr(Job.ReviewStatus, "REJECTED", "REJECTED"))


class APIClientProtocol(Protocol):
    def force_authenticate(self, *, user: Any) -> None: ...

    def post(self, path: str, data: Any | None = None, *, format: str | None = None) -> Any: ...

    def get(self, path: str) -> Any: ...


def build_client() -> APIClientProtocol:
    return cast(APIClientProtocol, _APIClient())


ModelT = TypeVar("ModelT")


def _manager_for(model: Type[ModelT]) -> Any:
    return cast(Any, getattr(model, "objects"))


def _current_time() -> datetime:
    time_source = cast(Any, timezone)
    return cast(datetime, time_source.now())


def _create(model: Type[ModelT], **kwargs: Any) -> ModelT:
    manager = _manager_for(model)
    result = manager.create(**kwargs)
    return cast(ModelT, result)


def _create_user(**kwargs: Any) -> User:
    return cast(User, _manager_for(User).create_user(**kwargs))


def _make_case(settings: Any) -> tuple[Case, User, User, User]:
    settings.PLATFORM_DEV_OPEN = False
    org = _create(Organization, id="ORG-REV", name="Review Org")
    case = _create(Case, id="CASE-REV", title="Review Case", organization=org)
    owner = _create_user(username="owner_rev", password="x", display_name="Owner R")
    reviewer = _create_user(username="reviewer_rev", password="x", display_name="Reviewer R")
    outsider = _create_user(username="outsider_rev", password="x")
    _create(CaseMembership, case=case, user=owner, role=CaseMembership.Role.OWNER)
    _create(CaseMembership, case=case, user=reviewer, role=CaseMembership.Role.REVIEWER)
    case.reviewer = reviewer
    cast(Any, case).save(update_fields=["reviewer"])
    return case, owner, reviewer, outsider


def _make_job(case: Case, *, status: str = Job.Status.SUCCEEDED) -> Job:
    job = _create(
        Job,
        case=case,
        audio_input=f"/tmp/{case.id}-{status}.wav",
        mode=Job.Mode.BATCH,
        diarization=True,
        language="en-CA",
        status=status,
    )
    now = _current_time()
    job.started_at = now
    job.finished_at = now
    job.duration_s = 12.5
    job.transcript_path = f"/tmp/{job.id}_transcript.txt"
    cast(Any, job).save(update_fields=["started_at", "finished_at", "duration_s", "transcript_path"])
    return job


def test_reviewer_can_approve_and_creates_artifact(db: Any, settings: Any) -> None:
    case, _owner, reviewer, _ = _make_case(settings)
    job = _make_job(case)
    job_any = cast(Any, job)
    reviewer_obj = cast(Any, reviewer)
    client = build_client()
    client.force_authenticate(user=reviewer_obj)

    resp: Any = client.post(f"/api/v1/jobs/{job.id}/approve/")
    assert resp.status_code == 200
    job_any.refresh_from_db()
    assert job_any.review_status == APPROVED_REVIEW_STATUS
    assert job_any.reviewed_by_id == reviewer_obj.id
    artifacts = _manager_for(CaseArtifact).filter(
        case_id=str(case.id), type="TRANSCRIPT_APPROVED", job_id=str(job.id)
    )
    assert artifacts.exists()
    payload = cast(dict[str, Any], resp.json())
    assert payload["review_status"] == "APPROVED"
    assert payload["reviewed_by"] == cast(str, reviewer_obj.display_name)


def test_reviewer_can_reject_and_removes_artifact(db: Any, settings: Any) -> None:
    case, _owner, reviewer, _ = _make_case(settings)
    job = _make_job(case)
    reviewer_obj = cast(Any, reviewer)
    _create(
        CaseArtifact,
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
    job_any = cast(Any, job)
    job_any.review_status = APPROVED_REVIEW_STATUS
    job_any.reviewed_by = reviewer
    job_any.reviewed_at = _current_time()
    job_any.save(update_fields=["review_status", "reviewed_by", "reviewed_at"])

    client = build_client()
    client.force_authenticate(user=reviewer_obj)
    resp: Any = client.post(f"/api/v1/jobs/{job.id}/reject/", {"comment": "needs work"}, format="json")
    assert resp.status_code == 200
    job_any.refresh_from_db()
    assert job_any.review_status == REJECTED_REVIEW_STATUS
    assert job_any.review_comment == "needs work"
    removal_qs = _manager_for(CaseArtifact).filter(
        case_id=str(case.id), type="TRANSCRIPT_APPROVED", job_id=str(job.id)
    )
    assert not removal_qs.exists()


def test_approve_requires_permission(db: Any, settings: Any) -> None:
    case, _owner, reviewer, outsider = _make_case(settings)
    job = _make_job(case)
    assert reviewer
    client = build_client()
    client.force_authenticate(user=outsider)
    resp: Any = client.post(f"/api/v1/jobs/{job.id}/approve/")
    assert resp.status_code in {403, 404}


def test_approve_requires_succeeded_job(db: Any, settings: Any) -> None:
    case, _owner, reviewer, _ = _make_case(settings)
    job = _make_job(case, status=Job.Status.RUNNING)
    client = build_client()
    client.force_authenticate(user=reviewer)
    resp: Any = client.post(f"/api/v1/jobs/{job.id}/approve/")
    assert resp.status_code == 400


def test_status_endpoint_includes_review_fields(db: Any, settings: Any) -> None:
    case, owner, _reviewer, _ = _make_case(settings)
    job = _make_job(case)
    job_any = cast(Any, job)
    owner_obj = cast(Any, owner)
    job_any.review_status = APPROVED_REVIEW_STATUS
    job_any.reviewed_by = owner
    job_any.reviewed_at = _current_time()
    job_any.review_comment = "looks good"
    job_any.review_activity_id = uuid.uuid4()
    job_any.save(
        update_fields=[
            "review_status",
            "reviewed_by",
            "reviewed_at",
            "review_comment",
            "review_activity_id",
        ]
    )

    client = build_client()
    client.force_authenticate(user=owner_obj)
    resp: Any = client.get(f"/api/v1/jobs/{job.id}/status/")
    assert resp.status_code == 200
    data = cast(dict[str, Any], resp.json())
    assert data["review_status"] == "APPROVED"
    assert data["review_comment"] == "looks good"
    assert data["reviewed_by"] == cast(str, owner_obj.display_name)
    assert data["review_activity_id"] == str(job_any.review_activity_id)


def test_update_job_meta_merges(db: Any, settings: Any) -> None:
    case, _owner, _reviewer, _ = _make_case(settings)
    job = _make_job(case)
    ops_directory = ops_dir(str(case.id), cast(str | None, case.organization_id))
    ops_directory.mkdir(parents=True, exist_ok=True)
    log_path = ops_directory / f"{job.id}_transcription_log.json"
    log_path.write_text(json.dumps({"existing": "value"}), encoding="utf-8")

    update_job_meta(
        str(case.id),
        cast(str | None, case.organization_id),
        str(job.id),
        {"audio_sha256": "abc", "audio_size_bytes": 1024, "audio_channels": None},
    )
    updated = json.loads(log_path.read_text(encoding="utf-8"))
    assert updated["existing"] == "value"
    assert updated["audio_sha256"] == "abc"
    assert updated["audio_size_bytes"] == 1024
    assert "audio_channels" not in updated


def test_notes_endpoint_updates_metadata(db: Any, settings: Any) -> None:
    case, _owner, reviewer, _ = _make_case(settings)
    ensure_case_dirs(str(case.id), cast(str | None, case.organization_id))
    job = _make_job(case)
    job_any = cast(Any, job)
    reviewer_obj = cast(Any, reviewer)
    client = build_client()
    client.force_authenticate(user=reviewer_obj)

    from django.urls import reverse  # type: ignore[reportMissingImports]

    url = cast(str, reverse("job-notes", args=[job.id]))
    resp: Any = client.post(url, {"notes": "Team note"}, format="json")
    assert resp.status_code == 200
    body = cast(dict[str, Any], resp.json())
    assert body["status"] == "ok"
    notes_payload = cast(dict[str, Any], body["notes"])
    assert notes_payload["count"] == 1
    entry = cast(dict[str, Any], notes_payload["entries"][0])
    assert entry["text"] == "Team note"

    resp_second: Any = client.post(url, {"notes": "Follow-up"}, format="json")
    assert resp_second.status_code == 200
    payload_second = cast(dict[str, Any], resp_second.json())
    assert payload_second["notes"]["count"] == 2
    texts = [cast(str, cast(dict[str, Any], item)["text"]) for item in payload_second["notes"]["entries"]]
    assert "Team note" in texts and "Follow-up" in texts
    first_entry = cast(dict[str, Any], payload_second["notes"]["entries"][0])
    assert cast(str, first_entry["text"]) == "Follow-up"

    stored_notes = list(cast(Sequence[JobNote], _manager_for(JobNote).filter(job=job_any).order_by("-created_at")))
    assert len(stored_notes) == 2
    stored_texts: set[str] = {cast(str, cast(Any, note).text) for note in stored_notes}
    assert {"Team note", "Follow-up"}.issubset(stored_texts)


def test_notes_endpoint_requires_permission(db: Any, settings: Any) -> None:
    case, _owner, _reviewer, outsider = _make_case(settings)
    ensure_case_dirs(str(case.id), cast(str | None, case.organization_id))
    job = _make_job(case)
    client = build_client()
    client.force_authenticate(user=outsider)

    resp: Any = client.post(f"/api/v1/jobs/{job.id}/notes/", {"notes": "should fail"}, format="json")
    assert resp.status_code in {403, 404}
