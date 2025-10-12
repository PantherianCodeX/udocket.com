from __future__ import annotations

import uuid
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.platform.accounts.models import Organization, OrganizationMembership
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from tests._typing import DatabaseFixture, SettingsFixture


def test_cases_list_anonymous(db: DatabaseFixture, settings: SettingsFixture):
    settings.PLATFORM_DEV_OPEN = True
    org = Organization.objects.create(name="Anon Org")
    Case.objects.create(id="CASE-1", title="Demo", organization=org)
    client = APIClient()
    resp = client.get("/api/v1/cases/")
    assert resp.status_code == 200
    data = resp.json()
    assert any(item["id"] == "CASE-1" for item in data)


def test_job_status_minimal(db: DatabaseFixture, settings: SettingsFixture):
    settings.PLATFORM_DEV_OPEN = True
    org = Organization.objects.create(name="Status Org")
    case = Case.objects.create(id="CASE-2", title="Demo2", organization=org)
    job = Job.objects.create(case=case, audio_input="/tmp/a.wav")
    client = APIClient()
    resp = client.get(f"/api/v1/jobs/{job.id}/status/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(job.id)
    assert data["status"] == Job.Status.PENDING


@pytest.mark.django_db
def test_case_create_requires_org_membership(db: DatabaseFixture, settings: SettingsFixture):
    settings.PLATFORM_DEV_OPEN = False
    User = get_user_model()
    user = User.objects.create_user(username="creator")
    org = Organization.objects.create(name="Org Case")
    OrganizationMembership.objects.create(
        organization=org,
        user=user,
        role=OrganizationMembership.Role.MANAGER,
    )

    client = APIClient()
    client.force_authenticate(user=user)
    payload = {"id": "CASE-MEM", "title": "Member Case", "organization": str(org.id)}
    resp = client.post("/api/v1/cases/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["id"] == "CASE-MEM"
    assert uuid.UUID(str(resp.data["organization"])) == org.id


@pytest.mark.django_db
def test_case_create_rejects_non_member(db: DatabaseFixture, settings: SettingsFixture):
    settings.PLATFORM_DEV_OPEN = False
    User = get_user_model()
    user = User.objects.create_user(username="outsider")
    org = Organization.objects.create(name="Org No Access")

    client = APIClient()
    client.force_authenticate(user=user)
    payload = {"id": "CASE-NON", "title": "Blocked Case", "organization": str(org.id)}
    resp = client.post("/api/v1/cases/", payload, format="json")
    assert resp.status_code == 403