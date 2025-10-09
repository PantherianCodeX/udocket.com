from __future__ import annotations

# pyright: strict

import logging
import os
from datetime import timedelta
from typing import Any, Iterable, Mapping, Protocol, Sequence, cast

from celery import shared_task
from django.utils import timezone

from apps.platform.jobs.models import Job
from apps.platform.operations.runtime import JobRuntimeContext, safe_job_log, safe_job_meta
from apps.platform.operations.utils import read_job_meta
from apps.platform.operations.task_modules.analyze import analyze_job as _analyze_job
from apps.platform.operations.task_modules.compose import compose_job as _compose_job
from apps.platform.operations.task_modules.transcribe import transcribe_job as _transcribe_job


class TaskProtocol(Protocol):
    request: Any


log = logging.getLogger("apps.platform.operations.tasks.recover")


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except Exception:
        return default


def _active_celery_task_ids(inspect_obj: Any, task_ids: Iterable[str]) -> set[str]:
    ids = [tid for tid in task_ids if tid]
    active: set[str] = set()
    if not ids:
        return active
    if inspect_obj is not None:
        for attr in ("active", "reserved", "scheduled"):
            try:
                data = getattr(inspect_obj, attr)()
            except Exception:
                data = None
            if not data:
                continue
            for tasks in data.values():
                for entry in tasks:
                    entry_id = entry.get("id") or entry.get("request", {}).get("id")
                    entry_state = entry.get("state") or entry.get("request", {}).get("state")
                    if entry_id in ids and entry_state in {None, "STARTED", "RETRY"}:
                        active.add(entry_id)
    return active


def _candidate_task_ids(meta: Mapping[str, object]) -> Sequence[str]:
    candidates: list[str] = []
    current = meta.get("celery_task_id")
    if isinstance(current, str) and current:
        candidates.append(current)
    history_val = meta.get("celery_task_history")
    if isinstance(history_val, Sequence) and not isinstance(history_val, (str, bytes, bytearray)):
        for item in cast(Sequence[object], history_val):
            if isinstance(item, str) and item:
                candidates.append(item)
    # Deduplicate while preserving order
    deduped: list[str] = []
    seen: set[str] = set()
    for tid in candidates:
        if tid not in seen:
            seen.add(tid)
            deduped.append(tid)
    return deduped


def _finalize_cancel(job: Job, *, reason: str | None = None) -> None:
    case_id = str(job.case_id)
    org_id = str(job.organization_id) if job.organization_id else None
    runtime = JobRuntimeContext(
        job=job,
        case_id=case_id,
        org_id=org_id,
        task_name="recover_stale_jobs",
        task_id="",
    )
    runtime.cancel(reason=reason or "Cancelled", log_message="Recovery: finalized cancellation")
    safe_job_meta(
        case_id,
        org_id,
        str(job.id),
        {"celery_task_status": "cancelled", "celery_task_finished_at": timezone.now().isoformat()},
    )


def _cannot_resume(job: Job, *, message: str) -> None:
    case_id = str(job.case_id)
    org_id = str(job.organization_id) if job.organization_id else None
    runtime = JobRuntimeContext(
        job=job,
        case_id=case_id,
        org_id=org_id,
        task_name="recover_stale_jobs",
        task_id="",
    )
    runtime.fail(error=message, log_message=f"Recovery failed: {message}")
    safe_job_meta(
        case_id,
        org_id,
        str(job.id),
        {"recovery_error": message, "recovered_at": timezone.now().isoformat()},
    )


@shared_task(bind=True)
def recover_stale_jobs(self: TaskProtocol) -> dict[str, object]:
    """Find unfinished jobs without an active worker and resume or close them.

    Strategy:
    - If job is CANCELLING and no worker is active, mark as CANCELLED.
    - If job is RUNNING/UPLOADING/CONVERTING with no worker, re-dispatch the original task.
    - If inputs are missing and resume isn't possible, mark as FAILED.
    """
    stale_minutes = max(1, _int_env("JOB_RECOVERY_STALE_MINUTES", 5))
    cutoff = timezone.now() - timedelta(minutes=stale_minutes)

    # Gather potentially stale jobs
    qs = Job.typed_objects().select_related("case").filter(
        status__in=(
            Job.Status.RUNNING,
            Job.Status.UPLOADING,
            Job.Status.CONVERTING,
            Job.Status.CANCELLING,
        ),
        finished_at__isnull=True,
    )
    candidates: list[Job] = []
    for job in qs.iterator():
        # Ignore very recent transitions to avoid flapping
        started_at = job.started_at or job.created_at
        if started_at and started_at > cutoff:
            continue
        candidates.append(job)

    if not candidates:
        return {"status": "ok", "checked": 0, "resumed": 0, "finalized": 0}

    # Inspect active tasks once
    try:
        from apps.platform.config.celery import app as celery_app

        inspect_obj = celery_app.control.inspect()
    except Exception:
        inspect_obj = None

    resumed = 0
    finalized = 0

    for job in candidates:
        case_id = str(job.case_id)
        job_id = str(job.id)
        org_id = str(job.organization_id) if job.organization_id else None
        meta = read_job_meta(case_id, org_id, job_id)
        task_ids = _candidate_task_ids(meta)
        active = _active_celery_task_ids(inspect_obj, task_ids) if task_ids else set()
        if active:
            continue

        # No active worker for this job
        if job.status == Job.Status.CANCELLING:
            _finalize_cancel(job, reason="No active worker during cancellation")
            finalized += 1
            continue

        # Attempt to resume based on job kind
        job_kind = (job.job_kind or str(meta.get("job_kind") or "")).strip().lower()
        agent_type = (getattr(job, "agent_type", "") or str(meta.get("agent_type") or "")).strip().lower()
        kind = job_kind or agent_type

        try:
            if kind in {"transcription", "transcribe", ""}:
                # Resume transcription with original job args
                if not job.audio_input:
                    _cannot_resume(job, message="Missing audio input path")
                    finalized += 1
                    continue
                safe_job_log(case_id, org_id, job_id, "Recovery: restarting transcription task")
                _transcribe_job.apply_async(
                    kwargs={
                        "case_id": case_id,
                        "job_id": job_id,
                        "audio_input": job.audio_input,
                        "mode": job.mode,
                        "diarization": job.diarization,
                        "language": job.language,
                    }
                )
                safe_job_meta(case_id, org_id, job_id, {"recovered_at": timezone.now().isoformat()})
                resumed += 1
                continue

            if kind in {"analyze", "analysis", "summary"}:
                safe_job_log(case_id, org_id, job_id, "Recovery: restarting analyze task")
                llm_cfg = cast(str | None, meta.get("requested_llm_config_id"))
                source_job_id = cast(str | None, meta.get("source_job_id"))
                _analyze_job.apply_async(
                    kwargs={
                        "case_id": case_id,
                        "job_id": job_id,
                        "llm_config_id": llm_cfg,
                        "source_job_id": source_job_id,
                    }
                )
                safe_job_meta(case_id, org_id, job_id, {"recovered_at": timezone.now().isoformat()})
                resumed += 1
                continue

            if kind in {"compose"}:
                safe_job_log(case_id, org_id, job_id, "Recovery: restarting compose task")
                summary_job_id = cast(str | None, meta.get("summary_job_id"))
                llm_cfg = cast(str | None, meta.get("requested_llm_config_id"))
                if not summary_job_id:
                    _cannot_resume(job, message="Missing summary_job_id for compose")
                    finalized += 1
                    continue
                _compose_job.apply_async(
                    kwargs={
                        "case_id": case_id,
                        "job_id": job_id,
                        "summary_job_id": summary_job_id,
                        "llm_config_id": llm_cfg,
                    }
                )
                safe_job_meta(case_id, org_id, job_id, {"recovered_at": timezone.now().isoformat()})
                resumed += 1
                continue

            # Unknown kind
            _cannot_resume(job, message=f"Unknown job kind: {kind or 'unset'}")
            finalized += 1
        except Exception as exc:  # noqa: BLE001
            log.exception("job recovery error", extra={"job_id": job_id, "error": str(exc)})
            _cannot_resume(job, message=f"Recovery error: {exc}")
            finalized += 1

    return {"status": "ok", "checked": len(candidates), "resumed": resumed, "finalized": finalized}
