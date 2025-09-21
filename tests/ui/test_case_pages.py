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
    assert "Transcription workflow" in html
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


@pytest.mark.django_db
def test_organization_switch_filters_cases(settings):
    settings.PLATFORM_DEV_OPEN = True
    org_a = Organization.objects.create(id="org-A", name="Alpha Org")
    org_b = Organization.objects.create(id="org-B", name="Beta Org")
    case_a = Case.objects.create(id="case-A", title="Alpha Case", organization=org_a)
    case_b = Case.objects.create(id="case-B", title="Beta Case", organization=org_b)
    user = User.objects.create_user(username="tenant-user", password="pw")
    CaseMembership.objects.create(case=case_a, user=user, role=CaseMembership.Role.OWNER)
    CaseMembership.objects.create(case=case_b, user=user, role=CaseMembership.Role.OWNER)

    client = Client()
    client.force_login(user)

    # Select org A
    client.post("/org/select/", {"organization_id": org_a.id, "next": "/"})
    html = client.get("/").content.decode()
    assert "Alpha Case" in html
    assert "Beta Case" not in html

    # Switch to org B
    client.post("/org/select/", {"organization_id": org_b.id, "next": "/"})
    html = client.get("/").content.decode()
    assert "Beta Case" in html
    assert "Alpha Case" not in html
