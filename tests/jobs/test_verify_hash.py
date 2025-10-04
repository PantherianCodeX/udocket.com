from __future__ import annotations

import hashlib
import json
from pathlib import Path

from rest_framework.test import APIClient

from apps.platform.accounts.models import Organization, User
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.jobs.models import Job
from apps.platform.operations.storage import ops_dir


def _setup_case_with_job(settings, storage_root: Path, *, mismatch: bool = False) -> tuple[Job, User, str]:
    settings.PLATFORM_DEV_OPEN = True
    settings.STORAGE_ROOT = str(storage_root)

    org = Organization.objects.create(name="Verify Org")
    case = Case.objects.create(id="CASE-VERIFY", title="Verify Case", organization=org)
    user = User.objects.create_user(username="verify_user", password="testpw")
    CaseMembership.objects.create(case=case, user=user, role=CaseMembership.Role.OWNER)

    audio_dir = storage_root / "media" / "cases" / str(case.id) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / "sample.wav"
    audio_bytes = b"hash-me"
    audio_path.write_bytes(audio_bytes)
    observed_hash = hashlib.sha256(audio_bytes).hexdigest()

    job = Job.objects.create(
        case=case,
        organization=org,
        audio_input=str(audio_path),
        mode=Job.Mode.BATCH,
        diarization=False,
        language="en-CA",
        status=Job.Status.SUCCEEDED,
    )

    ops_path = ops_dir(str(case.id), case.organization_id)
    ops_path.mkdir(parents=True, exist_ok=True)
    meta = {
        "audio_sha256": "deadbeef" if mismatch else observed_hash,
    }
    log_file = ops_path / f"{job.id}_transcription_log.json"
    log_file.write_text(json.dumps(meta), encoding="utf-8")

    return job, user, observed_hash


def test_verify_hash_audio_match(db, settings, tmp_path):
    job, user, observed_hash = _setup_case_with_job(settings, tmp_path / "storage-verify", mismatch=False)

    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.post(f"/api/v1/jobs/{job.id}/verify-hash/", {"target": "audio"}, format="json")

    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "match"
    assert data["observed"] == observed_hash


def test_verify_hash_audio_mismatch(db, settings, tmp_path):
    job, user, _ = _setup_case_with_job(settings, tmp_path / "storage-mismatch", mismatch=True)

    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.post(f"/api/v1/jobs/{job.id}/verify-hash/", {"target": "audio"}, format="json")

    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "mismatch"
    assert data["expected"] == "deadbeef"
    assert data["observed"] != data["expected"]


def test_refresh_audio_metadata_endpoint(db, settings, tmp_path):
    job, user, observed_hash = _setup_case_with_job(settings, tmp_path / "storage-refresh", mismatch=False)

    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.post(f"/api/v1/jobs/{job.id}/refresh-audio/")

    assert resp.status_code == 200
    payload = resp.json()
    assert "audio" in payload
    audio_payload = payload["audio"]
    assert audio_payload.get("sha256") == observed_hash
    assert audio_payload.get("size_bytes_local") or audio_payload.get("size_bytes_remote")
