from __future__ import annotations

import pytest

from django.test import Client

from apps.platform.accounts.models import Organization, User
from apps.platform.cases.models import Case, CaseMembership


@pytest.mark.django_db
def test_case_detail_renders_modern_layout(settings):
    settings.PLATFORM_DEV_OPEN = True
    org = Organization.objects.create(id="org-layout", name="Layout Org")
    case = Case.objects.create(id="case-layout", title="Layout Case", organization=org)
    user = User.objects.create_user(username="layout-user", password="pw")
    CaseMembership.objects.create(case=case, user=user, role=CaseMembership.Role.OWNER)

    client = Client()
    client.force_login(user)

    resp = client.get(f"/cases/{case.id}/")
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "Launch transcription" in html
    assert "Live updates" in html


@pytest.mark.django_db
def test_jobs_page_smoke_test(settings):
    settings.PLATFORM_DEV_OPEN = True
    org = Organization.objects.create(id="org-jobs", name="Jobs Org")
    case = Case.objects.create(id="jobs-case", title="Jobs Case", organization=org)
    user = User.objects.create_user(username="jobs-user", password="pw")
    CaseMembership.objects.create(case=case, user=user, role=CaseMembership.Role.OWNER)

    client = Client()
    client.force_login(user)
    resp = client.get("/jobs/")
    assert resp.status_code == 200
    assert "Recent transcription jobs" in resp.content.decode()
