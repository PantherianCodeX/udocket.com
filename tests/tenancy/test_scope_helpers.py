from __future__ import annotations

import pytest

from django.contrib.auth import get_user_model

from apps.platform.accounts.models import Organization, OrganizationMembership
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.jobs.models import Job
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.tenancy import scope_cases, scope_jobs, scope_artifacts


User = get_user_model()


@pytest.mark.django_db
def test_scope_helpers_respect_memberships():
    org_a = Organization.objects.create(id="ORG-A", name="Org A")
    org_b = Organization.objects.create(id="ORG-B", name="Org B")

    user_a = User.objects.create_user(username="user_a")
    user_b = User.objects.create_user(username="user_b")

    OrganizationMembership.objects.create(
        organization=org_a,
        user=user_a,
        role=OrganizationMembership.Role.MANAGER,
    )

    case_a = Case.objects.create(id="CASE-A", title="Case A", organization=org_a)
    case_b = Case.objects.create(id="CASE-B", title="Case B", organization=org_b)

    CaseMembership.objects.create(case=case_a, user=user_a, role=CaseMembership.Role.OWNER)

    job_a = Job.objects.create(case=case_a, audio_input="/tmp/a.wav")
    job_b = Job.objects.create(case=case_b, audio_input="/tmp/b.wav")

    art_a = CaseArtifact.objects.create(
        case_id=case_a.id,
        case_fk=case_a,
        job_id=str(job_b.id),
        organization=org_a,
        type="SUMMARY",
        title="Analyze",
        path="/tmp/summary.md",
        checksum="",
    )
    CaseArtifact.objects.create(
        case_id=case_b.id,
        case_fk=case_b,
        job_id=str(job_a.id),
        organization=org_b,
        type="SUMMARY",
        title="Analyze B",
        path="/tmp/summary_b.md",
        checksum="",
    )

    qs_cases = Case.objects.all()
    qs_jobs = Job.objects.all().select_related("case")
    qs_artifacts = CaseArtifact.objects.all().select_related("case_fk")

    assert list(scope_cases(qs_cases, user_a)) == [case_a]
    assert list(scope_cases(qs_cases, user_b)) == []

    assert list(scope_jobs(qs_jobs, user_a)) == [job_a]
    assert list(scope_jobs(qs_jobs, user_b)) == []

    assert list(scope_artifacts(qs_artifacts, user_a)) == [art_a]
    assert list(scope_artifacts(qs_artifacts, user_b)) == []
