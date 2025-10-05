from __future__ import annotations

import pytest

from rest_framework.test import APIClient

from apps.platform.accounts.models import Organization, User, OrganizationMembership
from apps.platform.cases.models import Case, CaseMembership
from tests._typing import SettingsFixture


@pytest.mark.django_db
def test_case_create_uses_user_organization(settings: SettingsFixture):
    settings.PLATFORM_DEV_OPEN = False
    org = Organization.objects.create(name="API Org")
    user = User.objects.create_user(username="creator", password="x")
    OrganizationMembership.objects.create(user=user, organization=org)

    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.post(
        "/api/v1/cases/",
        {"id": "api-case", "title": "API Created"},
        format="json",
    )
    assert resp.status_code == 201
    case = Case.objects.get(pk="api-case")
    assert case.organization == org


@pytest.mark.django_db
def test_case_update_cannot_change_organization(settings: SettingsFixture):
    settings.PLATFORM_DEV_OPEN = False
    org = Organization.objects.create(name="Stable Org")
    other = Organization.objects.create(name="New Org")
    user = User.objects.create_user(username="maintainer", password="x")
    OrganizationMembership.objects.create(user=user, organization=org)
    case = Case.objects.create(id="case-stable", title="Stable", organization=org)
    CaseMembership.objects.create(case=case, user=user, role=CaseMembership.Role.OWNER)

    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.patch(
        f"/api/v1/cases/{case.id}/",
        {"title": "Updated", "organization": other.id},
        format="json",
    )
    assert resp.status_code in {200, 202, 204}
    case.refresh_from_db()
    assert case.organization == org