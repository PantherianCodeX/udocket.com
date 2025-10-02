from __future__ import annotations

import pytest
from django.test import RequestFactory

from apps.platform.accounts.models import Organization
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.ui.views.job_tables import build_job_table_state


@pytest.mark.django_db()
def test_build_job_table_state_produces_unique_filter_options():
    rf = RequestFactory()
    org = Organization.objects.create(id="ORG-JOBS", name="Jobs Org")
    case = Case.objects.create(id="CASE-JOBS", title="Jobs Case", organization=org)

    Job.objects.create(
        case=case,
        organization=org,
        audio_input="/tmp/audio1.wav",
        status=Job.Status.SUCCEEDED,
        agent_type="transcription",
        job_kind="transcription",
        display_title="Transcript Job",
    )
    Job.objects.create(
        case=case,
        organization=org,
        audio_input="/tmp/audio2.wav",
        status=Job.Status.FAILED,
        agent_type="transcription",
        job_kind="transcription",
        display_title="Transcript Retry",
    )
    Job.objects.create(
        case=case,
        organization=org,
        audio_input="/tmp/audio3.wav",
        status=Job.Status.SUCCEEDED,
        agent_type="summary",
        job_kind="summary",
        display_title="Summary Job",
    )

    request = rf.get(
        "/jobs/",
        {
            "jobs_status": [Job.Status.SUCCEEDED, Job.Status.FAILED],
            "jobs_agent": ["transcription"],
            "jobs_page_size": 25,
        },
    )

    table_state = build_job_table_state(
        request,
        Job.objects.filter(case=case),
        prefix="jobs",
        include_case_filters=True,
    )

    status_filter = next(filter_payload for filter_payload in table_state.filters if filter_payload["id"] == "status")
    agent_filter = next(filter_payload for filter_payload in table_state.filters if filter_payload["id"] == "agent")

    status_values = [option["value"] for option in status_filter["options"]]
    agent_values = [option["value"] for option in agent_filter["options"]]

    assert len(status_values) == len(set(status_values))
    assert len(agent_values) == len(set(agent_values))
    assert table_state.param_prefix == "jobs"
    assert "jobs_status" in table_state.param_names
    assert table_state.filters_active == 3  # two statuses + one agent selection
    assert table_state.pagination["pages"] >= 1
    assert table_state.pagination["display_count"] == len(table_state.rows)
