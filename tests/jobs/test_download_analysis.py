from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.platform.accounts.models import Organization
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.jobs.models import Job
from apps.platform.operations.utils import update_job_meta
from apps.platform.operations.services import case_paths


@pytest.mark.django_db()
def test_download_analysis_returns_file(settings, tmp_path):
    settings.STORAGE_ROOT = str(tmp_path)
    settings.MEDIA_ROOT = str(tmp_path)
    settings.PLATFORM_DEV_OPEN = True

    org = Organization.objects.create(id="ORG-DL1", name="Org Download")
    case = Case.objects.create(id="CASE-DL1", title="Case Download", organization=org)

    user_model = get_user_model()
    user = user_model.objects.create_user(username="dl", email="dl@example.com", password="pass")
    CaseMembership.objects.create(case=case, user=user)

    job = Job.objects.create(case=case, organization=org, audio_input="/tmp/a.wav")

    case_dir, _, analysis_dir = case_paths(str(case.id), str(org.id))
    analysis_dir.mkdir(parents=True, exist_ok=True)
    summary_md = analysis_dir / f"{job.id}__summary_v1.md"
    summary_md.write_text("# Summary\nContent", encoding="utf-8")

    update_job_meta(
        str(case.id),
        str(org.id),
        str(job.id),
        {"summary_markdown_file": str(summary_md.relative_to(case_dir))},
    )

    client = APIClient()
    client.force_login(user)

    response = client.get(f"/api/v1/jobs/{job.id}/download-analysis/?kind=summary_markdown")
    assert response.status_code == 200
    assert response.get("Content-Disposition", "").endswith(f"{summary_md.name}\"")
    body_bytes = b"".join(response.streaming_content)
    assert body_bytes == summary_md.read_bytes()


@pytest.mark.django_db()
def test_download_analysis_missing_artifact(settings, tmp_path):
    settings.STORAGE_ROOT = str(tmp_path)
    settings.MEDIA_ROOT = str(tmp_path)
    settings.PLATFORM_DEV_OPEN = True

    org = Organization.objects.create(id="ORG-DL2", name="Org Missing")
    case = Case.objects.create(id="CASE-DL2", title="Case Missing", organization=org)

    user_model = get_user_model()
    user = user_model.objects.create_user(username="dl2", email="dl2@example.com", password="pass")
    CaseMembership.objects.create(case=case, user=user)

    job = Job.objects.create(case=case, organization=org, audio_input="/tmp/a.wav")

    client = APIClient()
    client.force_login(user)

    response = client.get(f"/api/v1/jobs/{job.id}/download-analysis/?kind=summary_markdown")
    assert response.status_code == 404
    assert response.json()["detail"] == "Artifact not found for requested kind."
