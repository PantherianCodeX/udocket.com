from __future__ import annotations

from pathlib import Path

import pytest
from rest_framework.test import APIClient

from apps.platform.accounts.models import Organization, User
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.jobs.models import Job


@pytest.fixture
def org_case(db):
    org = Organization.objects.create(name="Auth Org")
    case = Case.objects.create(id="CASE-AUTHZ", title="Auth Case", organization=org)
    return org, case


def test_contributor_cannot_update_case(org_case, settings):
    settings.PLATFORM_DEV_OPEN = False
    _, case = org_case
    owner = User.objects.create_user(username="owner", password="x")
    contributor = User.objects.create_user(username="contrib", password="x")
    CaseMembership.objects.create(case=case, user=owner, role=CaseMembership.Role.OWNER)
    CaseMembership.objects.create(case=case, user=contributor, role=CaseMembership.Role.CONTRIBUTOR)

    client = APIClient()

    client.force_authenticate(user=contributor)
    resp = client.patch(f"/api/v1/cases/{case.id}/", {"title": "Nope"}, format="json")
    assert resp.status_code == 403

    client.force_authenticate(user=owner)
    resp_ok = client.patch(f"/api/v1/cases/{case.id}/", {"title": "Updated"}, format="json")
    assert resp_ok.status_code == 200
    case.refresh_from_db()
    assert case.title == "Updated"


def test_reviewer_cannot_download_transcript(org_case, settings, tmp_path):
    settings.PLATFORM_DEV_OPEN = False
    _, case = org_case
    owner = User.objects.create_user(username="owner2", password="x")
    reviewer = User.objects.create_user(username="reviewer2", password="x")
    CaseMembership.objects.create(case=case, user=owner, role=CaseMembership.Role.OWNER)
    CaseMembership.objects.create(case=case, user=reviewer, role=CaseMembership.Role.REVIEWER)

    job = Job.objects.create(case=case, audio_input="/tmp/audio2.wav")
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("hello", encoding="utf-8")
    job.transcript_path = str(transcript_path)
    job.save(update_fields=["transcript_path"])

    client = APIClient()

    client.force_authenticate(user=reviewer)
    resp_forbidden = client.get(f"/api/v1/jobs/{job.id}/download/")
    assert resp_forbidden.status_code == 403

    client.force_authenticate(user=owner)
    resp_ok = client.get(f"/api/v1/jobs/{job.id}/download/")
    assert resp_ok.status_code == 200
