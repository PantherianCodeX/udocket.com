from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from apps.platform.accounts.models import Organization, OrganizationMembership, User
from apps.platform.cases.models import Case
from apps.platform.artifacts.models import CaseArtifact
from tests._typing import SettingsFixture


@pytest.mark.django_db()
def test_artifacts_page_lists_artifacts(settings: SettingsFixture):
    settings.PLATFORM_DEV_OPEN = True
    org = Organization.objects.create(name="Artifacts Org")
    user = User.objects.create_user("artifact-user", "artifact@example.com", "pass123")
    OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.MEMBER)

    case = Case.objects.create(id="CASE-AR", title="Artifacts Case", organization=org)
    CaseArtifact.objects.create(
        case_id=str(case.id),
        case_fk=case,
        organization=org,
        type="SUMMARY",
        title="Initial Summary",
        path="/tmp/summary.md",
    )

    client = Client()
    client.force_login(user)
    resp = client.get(reverse("ui-artifacts"))
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "Initial Summary" in content
    assert "Artifacts" in content