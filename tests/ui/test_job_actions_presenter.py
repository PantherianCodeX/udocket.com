from __future__ import annotations

import pytest

from apps.platform.accounts.models import Organization
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.ui.views.presenters.job_actions import build_job_action_entries


@pytest.mark.django_db()
def test_summary_job_actions_include_download_link():
    org = Organization.objects.create(id="ORG-ACTIONS", name="Actions Org")
    case = Case.objects.create(id="CASE-ACTIONS", title="Actions Case", organization=org)
    job = Job.objects.create(case=case, audio_input="/tmp/a.wav", status=Job.Status.SUCCEEDED)

    telemetry = {
        "metadata": {
            "job_kind": "summary",
        },
        "artifacts": [
            {
                "id": "42",
                "type": "SUMMARY",
                "download_url": "/api/v1/artifacts/42/download/",
            }
        ],
    }

    sections = build_job_action_entries(job, telemetry, can_review=False, is_child=False)

    # Flatten all action labels for inspection
    labels_to_href = {}
    for section in sections:
        for item in section["items"]:
            if "href" in item:
                labels_to_href[item["label"]] = item["href"]

    assert labels_to_href["Download summary"] == "/api/v1/artifacts/42/download/"
