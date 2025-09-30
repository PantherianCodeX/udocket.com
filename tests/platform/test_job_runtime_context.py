from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Tuple

import pytest
from django.utils import timezone

from apps.platform.accounts.models import Organization
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.operations import runtime


@pytest.mark.django_db()
def test_job_runtime_context_lifecycle(monkeypatch):
    org = Organization.objects.create(id="ORG-RUNTIME", name="Runtime Org")
    case = Case.objects.create(id="CASE-RUNTIME", title="Runtime Case", organization=org)
    job = Job.objects.create(case=case, audio_input="/tmp/source.wav")

    meta_calls: List[Tuple[str, str | None, str, Dict[str, Any]]] = []
    log_calls: List[Tuple[str, str | None, str, str]] = []
    event_calls: List[Dict[str, Any]] = []

    monkeypatch.setattr(
        runtime,
        "update_job_meta",
        lambda case_id, org_id, job_id, updates: meta_calls.append((case_id, org_id, job_id, updates)),
    )
    monkeypatch.setattr(
        runtime,
        "append_job_log",
        lambda case_id, org_id, job_id, message, level="INFO": log_calls.append((case_id, org_id, job_id, message)),
    )

    def _capture_event(job_id: str, *, event: str, case_id: str, status: str | None = None, **payload: Any) -> None:
        payload_copy = dict(payload)
        payload_copy.update({"job_id": job_id, "event": event, "case_id": case_id, "status": status})
        event_calls.append(payload_copy)

    monkeypatch.setattr(runtime, "send_job_update", _capture_event)

    runtime_ctx = runtime.JobRuntimeContext(
        job=job,
        case_id=str(case.id),
        org_id=str(org.id),
        task_name="transcribe_job",
        task_id="task-123",
        task_meta={"mode": "batch"},
    )

    started = runtime_ctx.start(
        status=Job.Status.RUNNING,
        log_message="Job started",
        event="job.started",
        meta_updates={"phase": "start"},
        job_updates={"upload_progress": 0.0},
    )

    job.refresh_from_db()
    assert job.status == Job.Status.RUNNING
    assert pytest.approx(job.started_at) == pytest.approx(started, abs=1e-6)
    assert job.upload_progress == 0.0

    runtime_ctx.transition(
        status=Job.Status.UPLOADING,
        log_message="Uploading",
        event="job.uploading",
        job_event_payload={"progress_percent": 10.0},
        job_updates={"upload_progress": 10.0},
        task_meta_updates={"progress": 10.0},
    )

    job.refresh_from_db()
    assert job.status == Job.Status.UPLOADING
    assert job.upload_progress == 10.0

    finished = runtime_ctx.succeed(
        log_message="Completed",
        meta_updates={"phase": "done"},
        job_updates={"upload_progress": None},
        events=[("job.summary", {"result": "ok"})],
        task_meta_updates={"duration_s": 12.5},
    )

    job.refresh_from_db()
    assert job.status == Job.Status.SUCCEEDED
    assert job.finished_at and job.finished_at >= started
    assert job.error_message is None
    assert job.upload_progress is None
    assert pytest.approx(finished, abs=1e-6) == pytest.approx(job.finished_at, abs=1e-6)

    # Task state tracking should capture metadata
    task_state = runtime_ctx.task_state
    assert task_state["status"] == Job.Status.SUCCEEDED
    assert task_state["task_id"] == "task-123"
    assert task_state["mode"] == "batch"
    assert task_state["duration_s"] == 12.5
    assert "started_at" in task_state and "finished_at" in task_state

    # Meta/log/event hooks captured expected payloads
    assert any(call[3].get("phase") == "start" for call in meta_calls)
    assert any(call[3].get("phase") == "done" for call in meta_calls)
    assert any(msg.endswith("Completed") for _, _, _, msg in log_calls)
    assert any(event["event"] == "job.started" for event in event_calls)
    assert any(event["event"] == "job.uploading" for event in event_calls)
    assert any(event["event"] == "job.succeeded" for event in event_calls)
    assert any(event["event"] == "job.summary" for event in event_calls)


@pytest.mark.django_db()
def test_job_runtime_context_fail_and_cancel(monkeypatch):
    org = Organization.objects.create(id="ORG-RUNTIME2", name="Runtime Org 2")
    case = Case.objects.create(id="CASE-RUNTIME2", title="Runtime Case 2", organization=org)
    job = Job.objects.create(case=case, audio_input="/tmp/source2.wav")

    event_calls: List[Dict[str, Any]] = []

    monkeypatch.setattr(runtime, "update_job_meta", lambda *args, **kwargs: None)
    monkeypatch.setattr(runtime, "append_job_log", lambda *args, **kwargs: None)

    def _capture_event(job_id: str, *, event: str, case_id: str, status: str | None = None, **payload: Any) -> None:
        payload_copy = dict(payload)
        payload_copy.update({"job_id": job_id, "event": event, "case_id": case_id, "status": status})
        event_calls.append(payload_copy)

    monkeypatch.setattr(runtime, "send_job_update", _capture_event)

    runtime_ctx = runtime.JobRuntimeContext(job=job, case_id=str(case.id), org_id=str(org.id))
    runtime_ctx.start(status=Job.Status.RUNNING)

    failure_time = runtime_ctx.fail(error="boom", log_message="Failed hard", meta_updates={"phase": "fail"})

    job.refresh_from_db()
    assert job.status == Job.Status.FAILED
    assert job.error_message == "boom"
    assert job.finished_at and job.finished_at >= failure_time - timedelta(seconds=1)

    cancel_time = runtime_ctx.cancel(reason="user", log_message="Cancelled by user")
    job.refresh_from_db()
    assert job.status == Job.Status.CANCELLED
    assert job.error_message == "user"
    assert job.finished_at and job.finished_at >= cancel_time - timedelta(seconds=1)

    assert any(event["event"] == "job.failed" for event in event_calls)
    assert any(event["event"] == "job.cancelled" for event in event_calls)
