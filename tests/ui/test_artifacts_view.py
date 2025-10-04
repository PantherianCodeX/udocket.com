from __future__ import annotations

import pytest
from django.urls import reverse

from apps.platform.accounts.models import Organization, OrganizationMembership, User
from apps.platform.cases.models import Case
from apps.platform.artifacts.models import CaseArtifact


@pytest.mark.django_db()
def test_artifacts_index_search_and_pagination(client, django_user_model):
    org = Organization.objects.create(name="Artifacts Org")
    user: User = django_user_model.objects.create_user(
        username="artifact-user",
        email="artifact@example.com",
        password="password",
    )
    OrganizationMembership.objects.create(
        organization=org,
        user=user,
        role=OrganizationMembership.Role.ADMIN,
    )

    case = Case.objects.create(id="CASE-ART", title="Artifact Case", organization=org)

    for idx in range(25):
        CaseArtifact.objects.create(
            case_id=str(case.id),
            case_fk=case,
            organization=org,
            job_id=f"JOB-{idx:02d}",
            type="TRANSCRIPT",
            title=f"Transcript {idx:02d}",
            path=f"storage/{idx:02d}.txt",
        )

    for idx in range(5):
        CaseArtifact.objects.create(
            case_id=str(case.id),
            case_fk=case,
            organization=org,
            job_id=f"MISC-{idx:02d}",
            type="TIMELINE",
            title=f"Timeline {idx:02d}",
            path=f"storage/timeline-{idx:02d}.json",
        )

    client.force_login(user)
    session = client.session
    session["admin_active_org_id"] = str(org.id)
    session.save()

    response = client.get(
        reverse("ui-artifacts"),
        {
            "artifacts_search": "Transcript",
            "artifacts_page_size": 10,
            "artifacts_page": 2,
        },
    )

    assert response.status_code == 200
    section = response.context["section"]
    table = section["tables"][0]

    assert table["param_prefix"] == "artifacts"
    assert "artifacts_search" in table["filter_param_names"]
    assert table["pagination"]["page"] == 2
    assert table["pagination"]["page_size"] == 10
    assert table["filters"][0]["value"] == "Transcript"
    assert table["filters_active"] == 1
    assert table["limit_value"] == 10
    assert table["limit_options"]
    assert len(table["rows"]) <= 10
    assert response.context["artifact_pagination"]["page"] == 2
    assert response.context["artifact_pagination"]["total"] == 25
