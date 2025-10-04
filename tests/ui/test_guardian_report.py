from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from apps.platform.accounts.models import Organization, User
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.artifacts.models import CaseArtifact


@pytest.mark.django_db()
def test_case_guardian_report_json(settings):
    settings.PLATFORM_DEV_OPEN = True

    org = Organization.objects.create(name="Guardian Org")
    case = Case.objects.create(id="CASE-GRD", title="Guardian Case", organization=org)
    user = User.objects.create_user(username="guardian-user", email="guardian@example.com", password="pass123")
    CaseMembership.objects.create(case=case, user=user, role=CaseMembership.Role.OWNER)

    CaseArtifact.objects.create(
        case_id=str(case.id),
        case_fk=case,
        organization=org,
        type="SUMMARY",
        title="Latest Summary",
        path="/tmp/summary.txt",
        metadata={
            "guardian_history": [
                {
                    "status": "rejected",
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

    url = reverse("ui-case-guardian-report", args=[case.id])
    resp = client.get(url, {"format": "json"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["stats"]["rejected"] == 1
    assert data["violations"][0]["violation"]["message"] == "Contains personal identifiers."
