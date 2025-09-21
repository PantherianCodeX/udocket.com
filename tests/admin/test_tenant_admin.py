from __future__ import annotations

import pytest

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory

from apps.platform.accounts.models import Organization, OrganizationMembership
from apps.platform.accounts.utils import set_active_admin_org_id
from apps.platform.cases.admin import CaseAdmin
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.artifacts.admin import CaseArtifactAdmin
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.jobs.admin import JobAdmin
from apps.platform.jobs.models import Job
from apps.platform.operations.admin import AuditEventAdmin, TaskRunAdmin
from apps.platform.operations.models import AuditEvent, TaskRun
from apps.platform.tenancy import scope_cases, scope_jobs


def _admin_request(user, path: str = "/admin/"):
    factory = RequestFactory()
    request = factory.get(path)
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    request.user = user
    return request


@pytest.mark.django_db
def test_case_admin_queryset_matches_scope(settings):
    settings.PLATFORM_DEV_OPEN = False
    org_allowed = Organization.objects.create(id="alpha", name="Alpha Org")
    org_blocked = Organization.objects.create(id="beta", name="Beta Org")

    user = get_user_model().objects.create_user(
        username="tenant", password="x", is_staff=True, is_superuser=False
    )
    OrganizationMembership.objects.create(user=user, organization=org_allowed)

    case_allowed = Case.objects.create(id="case-1", title="One", organization=org_allowed)
    CaseMembership.objects.create(case=case_allowed, user=user)
    Case.objects.create(id="case-2", title="Two", organization=org_blocked)

    case_admin = CaseAdmin(Case, admin.site)

    request = _admin_request(user, "/admin/cases/case/")
    scoped_qs = case_admin.get_queryset(request)
    expected_ids = list(scope_cases(Case.objects.all(), user).values_list("id", flat=True))
    assert list(scoped_qs.values_list("id", flat=True)) == expected_ids

    assert case_admin.has_view_permission(request, case_allowed) is True
    other_case = Case.objects.exclude(id=case_allowed.id).first()
    assert case_admin.has_view_permission(request, other_case) is False

    set_active_admin_org_id(request, org_allowed.id)
    filtered_qs = case_admin.get_queryset(request)
    assert filtered_qs.filter(organization=org_allowed).count() == filtered_qs.count()


@pytest.mark.django_db
def test_job_admin_queryset_matches_scope(settings):
    settings.PLATFORM_DEV_OPEN = False
    org_allowed = Organization.objects.create(id="alpha-jobs", name="Alpha Jobs")
    org_blocked = Organization.objects.create(id="beta-jobs", name="Beta Jobs")

    case_allowed = Case.objects.create(id="case-j1", title="Case One", organization=org_allowed)
    Case.objects.create(id="case-j2", title="Case Two", organization=org_blocked)

    user = get_user_model().objects.create_user(
        username="tenant-jobs", password="x", is_staff=True, is_superuser=False
    )
    OrganizationMembership.objects.create(user=user, organization=org_allowed)
    CaseMembership.objects.create(case=case_allowed, user=user)

    job_allowed = Job.objects.create(
        case=case_allowed,
        organization=org_allowed,
        mode=Job.Mode.ON_DEMAND,
        audio_input="/tmp/audio.wav",
        language="en-CA",
    )
    Job.objects.create(
        case=Case.objects.get(id="case-j2"),
        organization=org_blocked,
        mode=Job.Mode.ON_DEMAND,
        audio_input="/tmp/audio2.wav",
        language="en-CA",
    )

    job_admin = JobAdmin(Job, admin.site)

    request = _admin_request(user, "/admin/jobs/job/")
    scoped_qs = job_admin.get_queryset(request)
    expected_ids = list(scope_jobs(Job.objects.all(), user).values_list("id", flat=True))
    assert list(scoped_qs.values_list("id", flat=True)) == expected_ids

    assert job_admin.has_view_permission(request, job_allowed) is True
    other_job = Job.objects.exclude(id=job_allowed.id).first()
    assert job_admin.has_view_permission(request, other_job) is False

    set_active_admin_org_id(request, org_allowed.id)
    filtered_qs = job_admin.get_queryset(request)
    assert filtered_qs.filter(organization=org_allowed).count() == filtered_qs.count()


@pytest.mark.django_db
def test_case_admin_requires_staff(settings):
    settings.PLATFORM_DEV_OPEN = False
    org = Organization.objects.create(id="tenant-org", name="Tenant Org")
    user = get_user_model().objects.create_user(
        username="nostaff", password="x", is_staff=False, is_superuser=False
    )
    OrganizationMembership.objects.create(user=user, organization=org)
    case = Case.objects.create(id="case-nostaff", title="No Staff", organization=org)
    CaseMembership.objects.create(case=case, user=user)

    case_admin = CaseAdmin(Case, admin.site)
    request = _admin_request(user)

    assert case_admin.has_module_permission(request) is False
    assert case_admin.has_view_permission(request, case) is False


@pytest.mark.django_db
def test_job_admin_requires_staff(settings):
    settings.PLATFORM_DEV_OPEN = False
    org = Organization.objects.create(id="tenant-job-org", name="Tenant Job Org")
    case = Case.objects.create(id="case-job-nostaff", title="Job Case", organization=org)
    user = get_user_model().objects.create_user(
        username="jobsnostaff", password="x", is_staff=False, is_superuser=False
    )
    OrganizationMembership.objects.create(user=user, organization=org)
    CaseMembership.objects.create(case=case, user=user)
    job = Job.objects.create(
        case=case,
        organization=org,
        mode=Job.Mode.ON_DEMAND,
        audio_input="/tmp/audio.wav",
        language="en-CA",
    )

    job_admin = JobAdmin(Job, admin.site)
    request = _admin_request(user)

    assert job_admin.has_module_permission(request) is False
    assert job_admin.has_view_permission(request, job) is False


@pytest.mark.django_db
def test_artifact_admin_queryset_matches_scope(settings):
    settings.PLATFORM_DEV_OPEN = False
    org_allowed = Organization.objects.create(id="artifact-alpha", name="Artifact Alpha")
    org_blocked = Organization.objects.create(id="artifact-beta", name="Artifact Beta")

    case_allowed = Case.objects.create(id="artifact-case-1", title="Artifact One", organization=org_allowed)
    case_blocked = Case.objects.create(id="artifact-case-2", title="Artifact Two", organization=org_blocked)

    user = get_user_model().objects.create_user(
        username="artifact-staff", password="x", is_staff=True, is_superuser=False
    )
    OrganizationMembership.objects.create(user=user, organization=org_allowed)
    CaseMembership.objects.create(case=case_allowed, user=user)

    artifact_allowed = CaseArtifact.objects.create(
        case_id=case_allowed.id,
        case_fk=case_allowed,
        organization=org_allowed,
        job_id=None,
        type="TRANSCRIPT",
        title="Allowed",
        path="/tmp/allowed.txt",
    )
    CaseArtifact.objects.create(
        case_id=case_blocked.id,
        case_fk=case_blocked,
        organization=org_blocked,
        job_id=None,
        type="TRANSCRIPT",
        title="Blocked",
        path="/tmp/blocked.txt",
    )

    artifact_admin = CaseArtifactAdmin(CaseArtifact, admin.site)

    request = _admin_request(user, "/admin/artifacts/caseartifact/")
    scoped_qs = artifact_admin.get_queryset(request)
    assert list(scoped_qs.values_list("id", flat=True)) == [artifact_allowed.id]

    assert artifact_admin.has_view_permission(request, artifact_allowed) is True
    blocked_artifact = CaseArtifact.objects.exclude(id=artifact_allowed.id).first()
    assert artifact_admin.has_view_permission(request, blocked_artifact) is False

    set_active_admin_org_id(request, org_allowed.id)
    filtered_qs = artifact_admin.get_queryset(request)
    assert list(filtered_qs.values_list("organization_id", flat=True)) == [org_allowed.id] * filtered_qs.count()


@pytest.mark.django_db
def test_audit_event_admin_queryset_matches_scope(settings):
    settings.PLATFORM_DEV_OPEN = False
    org_allowed = Organization.objects.create(id="audit-alpha", name="Audit Alpha")
    org_blocked = Organization.objects.create(id="audit-beta", name="Audit Beta")

    case_allowed = Case.objects.create(id="audit-case-1", title="Audit One", organization=org_allowed)
    Case.objects.create(id="audit-case-2", title="Audit Two", organization=org_blocked)

    user = get_user_model().objects.create_user(
        username="audit-staff", password="x", is_staff=True, is_superuser=False
    )
    OrganizationMembership.objects.create(user=user, organization=org_allowed)
    CaseMembership.objects.create(case=case_allowed, user=user)

    allowed_event = AuditEvent.objects.create(case_id=case_allowed.id, event="ALLOWED", actor="user")
    AuditEvent.objects.create(case_id="audit-case-2", event="BLOCKED", actor="user")

    audit_admin = AuditEventAdmin(AuditEvent, admin.site)
    request = _admin_request(user, "/admin/operations/auditevent/")

    scoped_qs = audit_admin.get_queryset(request)
    assert list(scoped_qs.values_list("id", flat=True)) == [allowed_event.id]
    assert audit_admin.has_view_permission(request, allowed_event) is True
    blocked_event = AuditEvent.objects.exclude(id=allowed_event.id).first()
    assert audit_admin.has_view_permission(request, blocked_event) is False

    set_active_admin_org_id(request, org_allowed.id)
    filtered_qs = audit_admin.get_queryset(request)
    assert list(filtered_qs.values_list("id", flat=True)) == [allowed_event.id]


@pytest.mark.django_db
def test_task_run_admin_queryset_matches_scope(settings):
    settings.PLATFORM_DEV_OPEN = False
    org_allowed = Organization.objects.create(id="task-alpha", name="Task Alpha")
    org_blocked = Organization.objects.create(id="task-beta", name="Task Beta")

    case_allowed = Case.objects.create(id="task-case-1", title="Task One", organization=org_allowed)
    case_blocked = Case.objects.create(id="task-case-2", title="Task Two", organization=org_blocked)

    user = get_user_model().objects.create_user(
        username="task-staff", password="x", is_staff=True, is_superuser=False
    )
    OrganizationMembership.objects.create(user=user, organization=org_allowed)
    CaseMembership.objects.create(case=case_allowed, user=user)

    job_allowed = Job.objects.create(
        case=case_allowed,
        organization=org_allowed,
        mode=Job.Mode.ON_DEMAND,
        audio_input="/tmp/audio-task.wav",
        language="en-CA",
    )
    Job.objects.create(
        case=case_blocked,
        organization=org_blocked,
        mode=Job.Mode.ON_DEMAND,
        audio_input="/tmp/audio-blocked.wav",
        language="en-CA",
    )

    allowed_run = TaskRun.objects.create(
        task_name="jobs.transcribe",
        status="SUCCEEDED",
        job_id=str(job_allowed.id),
        case_id=case_allowed.id,
    )
    TaskRun.objects.create(
        task_name="jobs.transcribe",
        status="FAILED",
        job_id="blocked-job",
        case_id=case_blocked.id,
    )

    task_admin = TaskRunAdmin(TaskRun, admin.site)
    request = _admin_request(user, "/admin/operations/taskrun/")

    scoped_qs = task_admin.get_queryset(request)
    assert list(scoped_qs.values_list("id", flat=True)) == [allowed_run.id]
    assert task_admin.has_view_permission(request, allowed_run) is True
    blocked_run = TaskRun.objects.exclude(id=allowed_run.id).first()
    assert task_admin.has_view_permission(request, blocked_run) is False

    set_active_admin_org_id(request, org_allowed.id)
    filtered_qs = task_admin.get_queryset(request)
    assert list(filtered_qs.values_list("id", flat=True)) == [allowed_run.id]


@pytest.mark.django_db
def test_operations_admin_respects_superuser_active_org(settings):
    settings.PLATFORM_DEV_OPEN = False
    org_allowed = Organization.objects.create(id="ops-alpha", name="Ops Alpha")
    org_other = Organization.objects.create(id="ops-beta", name="Ops Beta")

    case_allowed = Case.objects.create(id="ops-case-1", title="Ops One", organization=org_allowed)
    case_other = Case.objects.create(id="ops-case-2", title="Ops Two", organization=org_other)

    job_allowed = Job.objects.create(
        case=case_allowed,
        organization=org_allowed,
        mode=Job.Mode.ON_DEMAND,
        audio_input="/tmp/audio-ops.wav",
        language="en-CA",
    )
    job_other = Job.objects.create(
        case=case_other,
        organization=org_other,
        mode=Job.Mode.ON_DEMAND,
        audio_input="/tmp/audio-other.wav",
        language="en-CA",
    )

    event_allowed = AuditEvent.objects.create(case_id=case_allowed.id, event="ALLOWED", actor="root")
    event_other = AuditEvent.objects.create(case_id=case_other.id, event="OTHER", actor="root")
    run_allowed = TaskRun.objects.create(
        task_name="jobs.transcribe",
        status="SUCCEEDED",
        job_id=str(job_allowed.id),
        case_id=case_allowed.id,
    )
    run_other = TaskRun.objects.create(
        task_name="jobs.transcribe",
        status="SUCCEEDED",
        job_id=str(job_other.id),
        case_id=case_other.id,
    )

    superuser = get_user_model().objects.create_superuser(username="root", password="x")
    audit_admin = AuditEventAdmin(AuditEvent, admin.site)
    task_admin = TaskRunAdmin(TaskRun, admin.site)

    request = _admin_request(superuser)
    assert set(audit_admin.get_queryset(request).values_list("id", flat=True)) == {event_allowed.id, event_other.id}
    assert set(task_admin.get_queryset(request).values_list("id", flat=True)) == {run_allowed.id, run_other.id}

    set_active_admin_org_id(request, org_allowed.id)
    scoped_events = set(audit_admin.get_queryset(request).values_list("id", flat=True))
    scoped_runs = set(task_admin.get_queryset(request).values_list("id", flat=True))
    assert scoped_events == {event_allowed.id}
    assert scoped_runs == {run_allowed.id}
