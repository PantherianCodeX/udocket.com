from __future__ import annotations

import json

from django.test import Client

from apps.platform.accounts.models import Organization, User
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.jobs.models import Job
from apps.platform.operations.storage import ops_dir


def _setup_case(settings):
    settings.PLATFORM_DEV_OPEN = False
    org = Organization.objects.create(id="ORG-PANEL", name="Panel Org")
    case = Case.objects.create(id="CASE-PANEL", title="Panel Case", organization=org)
    owner = User.objects.create_user(username="panel-owner", password="x")
    outsider = User.objects.create_user(username="panel-outsider", password="x")
    CaseMembership.objects.create(case=case, user=owner, role=CaseMembership.Role.OWNER)
    return case, owner, outsider


def _seed_job(case: Case) -> Job:
    job = Job.objects.create(
        case=case,
        audio_input="/tmp/panel-audio.wav",
        mode=Job.Mode.ON_DEMAND,
        status=Job.Status.SUCCEEDED,
    )
    ops = ops_dir(str(case.id), case.organization_id)
    ops.mkdir(parents=True, exist_ok=True)
    meta = {"status": job.status, "language": job.language, "word_count": 10}
    (ops / f"{job.id}_transcription_log.json").write_text(json.dumps(meta), encoding="utf-8")
    (ops / f"{job.id}_transcription.log").write_text("ok", encoding="utf-8")
    return job


def test_job_detail_panel_renders_for_member(db, settings):
    case, owner, _ = _setup_case(settings)
    job = _seed_job(case)

    client = Client()
    client.force_login(owner)
    resp = client.get(f"/jobs/{job.id}/detail-panel/")
    assert resp.status_code == 200
    content = resp.content.decode()
    assert str(job.id) in content
    assert "Download log" in content


def test_job_detail_panel_denies_non_member(db, settings):
    case, _, outsider = _setup_case(settings)
    job = _seed_job(case)

    client = Client()
    client.force_login(outsider)
    resp = client.get(f"/jobs/{job.id}/detail-panel/")
    assert resp.status_code == 404
