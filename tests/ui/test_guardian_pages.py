from __future__ import annotations

import pytest
from django.urls import reverse
from django.test import Client

from apps.platform.accounts.models import Organization, OrganizationMembership, User
from apps.platform.cases.models import Case
from apps.platform.artifacts.models import CaseArtifact


@pytest.mark.django_db()
def test_guardian_overview_page(settings):
    settings.PLATFORM_DEV_OPEN = True
    org = Organization.objects.create(name="Guardian Audit")
    user = User.objects.create_user("guardian-user", "guardian@example.com", "pass123")
    OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.MEMBER)

    case = Case.objects.create(id="CASE-GA", title="Guardian Case", organization=org)
    CaseArtifact.objects.create(
        case_id=str(case.id),
        case_fk=case,
        organization=org,
        type="SUMMARY",
        title="Hearing summary",
        path="/tmp/summary.txt",
        metadata={
            "guardian_history": [
                {
                    "status": "rejected",
                    "provider": "guardian-ai",
                    "reviewed_at": "2025-05-01T12:30:00Z",
                    "violations": [
                        {"severity": "HIGH", "message": "Contains personal identifiers."}
                    ],
                }
            ]
        },
    )

    client = Client()
    client.force_login(user)
    resp = client.get(reverse("ui-guardian-overview"))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "Guardian oversight" in body
    assert "Flagged" in body


@pytest.mark.django_db()
def test_guardian_report_json(settings):
    settings.PLATFORM_DEV_OPEN = True
    org = Organization.objects.create(name="Guardian Org")
    user = User.objects.create_user("guardian-report", "report@example.com", "pass123")
    OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.MEMBER)

    case = Case.objects.create(id="CASE-GR", title="Guardian Case", organization=org)
    CaseArtifact.objects.create(
        case_id=str(case.id),
        case_fk=case,
        organization=org,
        type="SUMMARY",
        title="Summary",
        path="/tmp/summary.txt",
        metadata={
            "guardian_history": [
                {
                    "status": "rejected",
                    "reviewed_at": "2025-07-01T10:00:00Z",
                    "violations": [
                        {"severity": "MEDIUM", "message": "Sensitive detail present."}
                    ],
                }
            ]
        },
    )

    client = Client()
    client.force_login(user)
    resp = client.get(reverse("ui-guardian-report"), {"format": "json"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["stats"]["rejected"] == 1
    assert data["violations"][0]["violation"]["message"] == "Sensitive detail present."
