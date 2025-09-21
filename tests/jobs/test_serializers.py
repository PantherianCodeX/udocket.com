from __future__ import annotations

from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIRequestFactory

from apps.platform.accounts.models import Organization, User
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.jobs.models import Job
from apps.platform.jobs.serializers import JobSerializer


def _make_job(case: Case) -> Job:
    job = Job.objects.create(
        case=case,
        audio_input="/tmp/test-audio.wav",
        mode=Job.Mode.ON_DEMAND,
    )
    job.transcript_path = "/tmp/test-transcript.txt"
    job.save(update_fields=["transcript_path"])
    return job


def test_job_serializer_field_visibility_by_role(db, settings):
    settings.PLATFORM_DEV_OPEN = False
    factory = APIRequestFactory()

    org = Organization.objects.create(id="ORG-JOBS", name="Jobs Org")
    case = Case.objects.create(id="CASE-JOBS", title="Jobs Case", organization=org)
    job = _make_job(case)

    owner = User.objects.create_user(username="owner", password="x")
    contributor = User.objects.create_user(username="contrib", password="x")
    reviewer = User.objects.create_user(username="reviewer", password="x")

    CaseMembership.objects.create(case=case, user=owner, role=CaseMembership.Role.OWNER)
    CaseMembership.objects.create(case=case, user=contributor, role=CaseMembership.Role.CONTRIBUTOR)
    CaseMembership.objects.create(case=case, user=reviewer, role=CaseMembership.Role.REVIEWER)

    req_owner = factory.get("/")
    req_owner.user = owner
    data_owner = JobSerializer(instance=job, context={"request": req_owner}).data
    assert data_owner.get("audio_input") == job.audio_input
    assert data_owner.get("transcript_path") == job.transcript_path

    req_contrib = factory.get("/")
    req_contrib.user = contributor
    data_contrib = JobSerializer(instance=job, context={"request": req_contrib}).data
    assert data_contrib.get("audio_input") == job.audio_input
    assert data_contrib.get("transcript_path") == job.transcript_path

    req_reviewer = factory.get("/")
    req_reviewer.user = reviewer
    data_reviewer = JobSerializer(instance=job, context={"request": req_reviewer}).data
    assert "audio_input" not in data_reviewer
    assert "transcript_path" not in data_reviewer

    req_anon = factory.get("/")
    req_anon.user = AnonymousUser()
    data_anon = JobSerializer(instance=job, context={"request": req_anon}).data
    assert "audio_input" not in data_anon
    assert "transcript_path" not in data_anon
