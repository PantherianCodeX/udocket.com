from __future__ import annotations

# pyright: strict

import os
from datetime import datetime, timedelta
from typing import Final

from django.utils import timezone

from apps.platform.jobs.models import Job

DEFAULT_STALE_MINUTES: Final = 180
TEAM_STALE_ENV: Final = "TEAM_ALERTS_STALE_MINUTES"
RECOVERY_STALE_ENV: Final = "JOB_RECOVERY_STALE_MINUTES"
ACTIVE_STALL_STATUSES: Final = {
    Job.Status.RUNNING,
    Job.Status.CONVERTING,
    Job.Status.UPLOADING,
    Job.Status.CANCELLING,
}


def _positive_int_env(name: str) -> int | None:
    raw = os.getenv(name)
    if not raw:
        return None
    try:
        value = int(raw.strip())
    except ValueError:
        return None
    return value if value > 0 else None


def job_activity_timestamp(job: Job) -> datetime | None:
    started_at = getattr(job, "started_at", None)
    if isinstance(started_at, datetime):
        return started_at
    created_at = getattr(job, "created_at", None)
    return created_at if isinstance(created_at, datetime) else None


def job_stale_cutoff(reference: datetime | None = None) -> datetime:
    now = reference or timezone.now()
    minutes = DEFAULT_STALE_MINUTES
    team_override = _positive_int_env(TEAM_STALE_ENV)
    if team_override is not None:
        minutes = max(1, team_override)
    else:
        recovery_override = _positive_int_env(RECOVERY_STALE_ENV)
        if recovery_override is not None:
            minutes = max(minutes, max(1, recovery_override) * 12)
    return now - timedelta(minutes=minutes)


def job_is_stalled(job: Job, *, reference: datetime | None = None) -> bool:
    status_value = getattr(job, "status", "")
    stalled_value = getattr(Job.Status, "STALLED", "STALLED")
    if status_value == stalled_value:
        return True
    if status_value not in ACTIVE_STALL_STATUSES:
        return False
    activity_ts = job_activity_timestamp(job)
    if activity_ts is None:
        return False
    if getattr(job, "finished_at", None):
        return False
    if activity_ts.tzinfo is None:
        activity_ts = timezone.make_aware(activity_ts)
    cutoff = job_stale_cutoff(reference)
    return activity_ts < cutoff
