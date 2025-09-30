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
