from typing import Any, Dict

import pytest

from apps.platform.accounts.models import Organization
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.ui.views.presenters import jobs as presenters


def _make_case_with_job() -> tuple[Case, Job]:
    org = Organization.objects.create(id="ORG-JOBS", name="Jobs Org")
    case = Case.objects.create(id="CASE-JOBS", title="Jobs Case", organization=org)
    job = Job.objects.create(
        case=case,
        audio_input="/tmp/sample.wav",
        mode=Job.Mode.BATCH,
        status=Job.Status.SUCCEEDED,
    )
    return case, job


@pytest.mark.django_db()
def test_jobs_by_agent_matches_summary_metadata():
    _, job = _make_case_with_job()

    telemetry_map = {
        str(job.id): {
            "metadata": {
                "summary_file": "/tmp/summary.md",
            }
        }
    }

    display_rows, _ = presenters.build_job_rows([job], telemetry_map)

    summary_rows = presenters.jobs_by_agent(
        display_rows,
        keywords=("summary", "summarization", "summarize"),
    )

    assert len(summary_rows) == 1
    assert summary_rows[0]["job"].id == job.id

    timeline_rows = presenters.jobs_by_agent(display_rows, keywords=("timeline", "event"))
    assert timeline_rows == []


@pytest.mark.django_db()
def test_build_job_rows_includes_running_summary_job_status():
    case, job = _make_case_with_job()
    job.status = Job.Status.RUNNING
    job.mode = Job.Mode.ON_DEMAND
    job.save(update_fields=["status", "mode"])

    telemetry_map = {
        str(job.id): {
            "status": Job.Status.RUNNING,
            "metadata": {
                "job_kind": "summary",
                "summary_file": "/tmp/summary.md",
            },
        }
    }

    display_rows, _ = presenters.build_job_rows([job], telemetry_map)
    assert len(display_rows) == 1

    row = display_rows[0]
    table_meta = row["table"]
    assert table_meta["status_display"] == "Running"
    assert "running" in table_meta["filter"]
    assert table_meta["job_kind"] == "summary"


@pytest.mark.django_db()
def test_build_job_rows_retains_all_parent_jobs():
    case, first_job = _make_case_with_job()
    second_job = Job.objects.create(
        case=case,
        audio_input="/tmp/second.wav",
        mode=Job.Mode.ON_DEMAND,
        status=Job.Status.PENDING,
    )

    telemetry_map = {
        str(first_job.id): {"status": Job.Status.SUCCEEDED},
        str(second_job.id): {"status": Job.Status.PENDING},
    }

    display_rows, _ = presenters.build_job_rows([first_job, second_job], telemetry_map)

    assert {row["job"].id for row in display_rows} == {first_job.id, second_job.id}


def _row(job: Job, metadata: Dict[str, object], *, title: str = "Job") -> Dict[str, Any]:
    return {
        "job": job,
        "telemetry": {"metadata": metadata},
        "title": title,
        "children": [],
        "is_child": False,
        "group_id": str(job.id),
        "root_id": str(job.id),
        "parent_id": "",
    }


@pytest.mark.django_db()
def test_jobs_by_agent_excludes_non_matching_parents():
    case, parent_job = _make_case_with_job()
    child_job = Job.objects.create(case=case, audio_input="/tmp/summary.wav", status=Job.Status.SUCCEEDED)

    parent_row = _row(parent_job, {"job_kind": "transcription"}, title="Transcription Parent")
    child_row = _row(
        child_job,
        {
            "job_kind": "summary",
            "summary_file": "/tmp/summary.txt",
        },
        title="Summary Child",
    )
    child_row["is_child"] = True
    child_row["parent_id"] = parent_row["group_id"]
    child_row["root_id"] = parent_row["group_id"]
    parent_row["children"] = [child_row]

    rows = presenters.jobs_by_agent([parent_row], keywords=("summary",))

    assert len(rows) == 1
    assert rows[0]["job"].id == child_job.id
