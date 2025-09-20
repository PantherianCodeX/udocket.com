from __future__ import annotations

import uuid
from rest_framework.test import APIClient
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job


def test_cases_list_anonymous(db, settings):
    settings.PLATFORM_DEV_OPEN = True
    Case.objects.create(id="CASE-1", title="Demo")
    client = APIClient()
    resp = client.get("/api/v1/cases/")
    assert resp.status_code == 200
    data = resp.json()
    assert any(item["id"] == "CASE-1" for item in data)


def test_job_status_minimal(db, settings):
    settings.PLATFORM_DEV_OPEN = True
    case = Case.objects.create(id="CASE-2", title="Demo2")
    job = Job.objects.create(case=case, audio_input="/tmp/a.wav")
    client = APIClient()
    resp = client.get(f"/api/v1/jobs/{job.id}/status/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(job.id)
    assert data["status"] == Job.Status.PENDING
